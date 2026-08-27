from datetime import date, datetime, timezone
from threading import Lock
from typing import List, Optional

from pydantic import BaseModel

from quantlab.cache import MarketCache
from quantlab.errors import DataUnavailableError
from quantlab.models import PriceBar, ResponseMeta
from quantlab.providers.base import MarketDataProvider, ProviderError, normalize_code
from quantlab.services.quality import validate_bars


FATAL_QUALITY_ERRORS = (
    "INVALID_OHLC",
    "DUPLICATE",
    "UNSORTED_DATES",
    "EXTREME_DAILY_RETURN",
    "MIXED_CODES",
    "MIXED_SOURCES",
)

# Fixed stripes avoid an unbounded lock registry while still coalescing the
# parallel market/analysis requests for the same security and provider.
FETCH_LOCKS = tuple(Lock() for _ in range(64))


class MarketDataResult(BaseModel):
    bars: List[PriceBar]
    meta: ResponseMeta


class MarketDataService:
    def __init__(
        self,
        cache: MarketCache,
        primary: MarketDataProvider,
        fallback: Optional[MarketDataProvider] = None,
    ):
        self.cache = cache
        self.primary = primary
        self.fallback = fallback

    @property
    def providers(self) -> list[MarketDataProvider]:
        return [provider for provider in (self.primary, self.fallback) if provider]

    @staticmethod
    def _fatal_quality_errors(bars: List[PriceBar]) -> list[str]:
        return [
            warning
            for warning in validate_bars(bars)
            if warning.startswith(FATAL_QUALITY_ERRORS)
        ]

    def _rank_providers(
        self, code: str, start: date, end: date
    ) -> list[MarketDataProvider]:
        preferred = self.cache.get_preferred_provider(code)
        configured_priority = {
            provider.name: index for index, provider in enumerate(self.providers)
        }
        return sorted(
            self.providers,
            key=lambda provider: (
                0 if provider.name == preferred else 1,
                -self.cache.coverage_days(provider.name, code, start, end),
                configured_priority[provider.name],
            ),
        )

    def _full_cached_result(
        self,
        providers: list[MarketDataProvider],
        code: str,
        start: date,
        end: date,
    ) -> tuple[MarketDataProvider, List[PriceBar]] | None:
        for provider in providers:
            if self.cache.missing_ranges(provider.name, code, start, end):
                continue
            cached = self.cache.get_bars(provider.name, code, start, end)
            if cached and not self._fatal_quality_errors(cached):
                return provider, cached
        return None

    def _load_provider(
        self,
        provider: MarketDataProvider,
        code: str,
        start: date,
        end: date,
        refresh: bool,
    ) -> tuple[List[PriceBar], bool]:
        dataset = provider.name
        ranges = (
            [(start, end)]
            if refresh
            else self.cache.missing_ranges(dataset, code, start, end)
        )
        if not ranges:
            cached = self.cache.get_bars(dataset, code, start, end)
            if not cached or self._fatal_quality_errors(cached):
                raise ProviderError(provider.name, code, "Invalid cached series")
            return cached, True

        fetched_by_range: list[tuple[date, date, List[PriceBar]]] = []
        for range_start, range_end in ranges:
            new_bars = provider.get_daily(code, range_start, range_end)
            if not new_bars:
                raise ProviderError(provider.name, code, "Empty response")
            if self._fatal_quality_errors(new_bars):
                raise ProviderError(provider.name, code, "Invalid provider response")
            fetched_by_range.append((range_start, range_end, new_bars))

        cached = [] if refresh else self.cache.get_bars(dataset, code, start, end)
        combined_by_date = {bar.trade_date: bar for bar in cached}
        for _, _, new_bars in fetched_by_range:
            combined_by_date.update({bar.trade_date: bar for bar in new_bars})
        combined = sorted(combined_by_date.values(), key=lambda bar: bar.trade_date)
        if self._fatal_quality_errors(combined):
            raise ProviderError(
                provider.name, code, "Invalid combined cached/provider series"
            )

        if refresh:
            self.cache.replace_range(dataset, code, start, end, combined)
        else:
            for range_start, range_end, new_bars in fetched_by_range:
                self.cache.upsert_bars(dataset, new_bars)
                self.cache.mark_synced(dataset, code, range_start, range_end)

        return combined, False

    def _load_provider_singleflight(
        self,
        provider: MarketDataProvider,
        code: str,
        start: date,
        end: date,
        refresh: bool,
    ) -> tuple[List[PriceBar], bool]:
        lock_key = (self.cache.db_path, provider.name, code)
        lock = FETCH_LOCKS[hash(lock_key) % len(FETCH_LOCKS)]
        with lock:
            return self._load_provider(provider, code, start, end, refresh)

    def _valid_stale_cache(
        self, provider: MarketDataProvider, code: str, start: date, end: date
    ) -> List[PriceBar]:
        cached = self.cache.get_bars(provider.name, code, start, end)
        if cached and not self._fatal_quality_errors(cached):
            return cached
        return []

    def _cross_check(
        self,
        code: str,
        bars: List[PriceBar],
        warnings: list[str],
    ) -> None:
        if not self.fallback:
            return
        primary_last20 = sorted(bars, key=lambda bar: bar.trade_date)[-20:]
        if not primary_last20:
            return
        try:
            fallback_bars = self.fallback.get_daily(
                code,
                primary_last20[0].trade_date,
                primary_last20[-1].trade_date,
            )
        except ProviderError:
            return
        fallback_by_date = {bar.trade_date: bar for bar in fallback_bars}
        for primary_bar in primary_last20:
            fallback_bar = fallback_by_date.get(primary_bar.trade_date)
            if not fallback_bar:
                continue
            close_diff = abs(primary_bar.close - fallback_bar.close)
            if close_diff > max(0.001, primary_bar.close * 0.001):
                warnings.append(
                    f"SOURCE_DIFFERENCE:{primary_bar.trade_date.isoformat()}:close"
                )
            volume_diff = abs(primary_bar.volume - fallback_bar.volume)
            if primary_bar.volume > 0 and volume_diff / primary_bar.volume > 0.05:
                warnings.append(
                    f"SOURCE_DIFFERENCE:{primary_bar.trade_date.isoformat()}:volume"
                )

    def get_daily(
        self,
        code: str,
        start: date,
        end: date,
        refresh: bool = False,
    ) -> MarketDataResult:
        code = normalize_code(code)
        warnings: list[str] = []
        ranked_providers = self._rank_providers(code, start, end)

        if not refresh:
            cached_result = self._full_cached_result(
                ranked_providers, code, start, end
            )
            if cached_result:
                selected_provider, bars = cached_result
                return MarketDataResult(
                    bars=bars,
                    meta=ResponseMeta(
                        sources=[selected_provider.name],
                        fetched_at=datetime.now(timezone.utc),
                        cache_hit=True,
                        is_demo=selected_provider.name.lower() == "demo",
                        warnings=[],
                    ),
                )

        bars: List[PriceBar] = []
        selected_provider = ranked_providers[0]
        cache_hit = False
        for provider in ranked_providers:
            if not refresh and self.cache.provider_in_cooldown(code, provider.name):
                warnings.append(f"PROVIDER_COOLDOWN:{provider.name}")
                continue
            try:
                bars, cache_hit = self._load_provider_singleflight(
                    provider, code, start, end, refresh
                )
                selected_provider = provider
                if not cache_hit:
                    self.cache.record_provider_success(code, provider.name)
                break
            except ProviderError:
                self.cache.record_provider_failure(code, provider.name)
                if provider is self.primary:
                    warnings.append("PRIMARY_PROVIDER_FAILED")

        if not bars:
            for provider in ranked_providers:
                bars = self._valid_stale_cache(provider, code, start, end)
                if bars:
                    selected_provider = provider
                    cache_hit = True
                    warnings.append("STALE_CACHE")
                    break

        if not bars:
            raise DataUnavailableError(code, len(ranked_providers))

        if refresh and selected_provider is self.primary:
            self._cross_check(code, bars, warnings)

        return MarketDataResult(
            bars=bars,
            meta=ResponseMeta(
                sources=[selected_provider.name],
                fetched_at=datetime.now(timezone.utc),
                cache_hit=cache_hit,
                is_demo=selected_provider.name.lower() == "demo",
                warnings=warnings,
            ),
        )
