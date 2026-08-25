from __future__ import annotations

from queue import Empty, Queue
from threading import Lock, Thread
from time import monotonic
from typing import Any

import numpy as np
import pandas as pd

from quantlab.errors import InstrumentNotFoundError
from quantlab.models import AssetProfile, Availability, EquityProfile, EtfProfile, Instrument
from quantlab.providers.base import ProviderError, normalize_code


def _missing(value: Any) -> bool:
    return value is None or value == "" or value == [] or value == {}


class AssetService:
    profile_ttl_seconds = 10 * 60
    primary_timeout_seconds = 6
    primary_cooldown_seconds = 60

    def __init__(self, provider: Any, fallback: Any | None = None):
        self.provider = provider
        self.fallback = fallback
        self._profile_cache: dict[str, tuple[float, AssetProfile, list[str]]] = {}
        self._lock = Lock()
        self._primary_slow_until = 0.0

    def _primary_call(self, operation, code: str):
        if monotonic() < self._primary_slow_until:
            raise ProviderError(getattr(self.provider, "name", "primary"), code, "主数据源冷却中")
        result: Queue = Queue(maxsize=1)

        def run() -> None:
            try:
                result.put((True, operation()))
            except Exception as exc:
                result.put((False, exc))

        worker = Thread(target=run, daemon=True)
        worker.start()
        try:
            succeeded, value = result.get(timeout=self.primary_timeout_seconds)
        except Empty as exc:
            self._primary_slow_until = monotonic() + self.primary_cooldown_seconds
            raise ProviderError(getattr(self.provider, "name", "primary"), code, "主数据源响应超时") from exc
        if not succeeded:
            raise value
        self._primary_slow_until = 0.0
        return value

    @property
    def provider_names(self) -> list[str]:
        return [getattr(item, "name", item.__class__.__name__) for item in (self.provider, self.fallback) if item is not None]

    def search(self, query: str) -> list[Instrument]:
        try:
            results = self._primary_call(lambda: self.provider.search(query), query)
            if results:
                return results
        except (ProviderError, InstrumentNotFoundError):
            pass
        if self.fallback is not None:
            return self.fallback.search(query)
        return []

    def get_instrument(self, code: str) -> Instrument:
        code = normalize_code(code)
        try:
            return self._primary_call(lambda: self.provider.get_instrument(code), code)
        except (ProviderError, InstrumentNotFoundError) as primary_error:
            if self.fallback is not None:
                return self.fallback.get_instrument(code)
            raise primary_error

    def _fetch(self, provider: Any, asset_type: str, code: str) -> dict[str, Any]:
        method_name = "get_etf_profile" if asset_type == "etf" else "get_equity_profile"
        method = getattr(provider, method_name, None)
        if method is None:
            return {}
        return method(code) or {}

    def _needs_fallback(self, asset_type: str, profile: dict[str, Any]) -> bool:
        required = (
            ("tracking_index", "manager", "size", "holdings")
            if asset_type == "etf"
            else ("industry", "pe", "pb", "total_market_cap", "financial_periods")
        )
        return any(_missing(profile.get(key)) for key in required)

    def _base_profile(self, code: str, instrument: Instrument) -> tuple[AssetProfile, list[str]]:
        primary_profile: dict[str, Any] = {}
        fallback_profile: dict[str, Any] = {}
        errors: list[Exception] = []
        sources: list[str] = []
        try:
            primary_profile = self._primary_call(lambda: self._fetch(self.provider, instrument.asset_type, code), code)
            if primary_profile:
                sources.append(getattr(self.provider, "name", self.provider.__class__.__name__))
        except Exception as exc:
            errors.append(exc)

        if self.fallback is not None and self._needs_fallback(instrument.asset_type, primary_profile):
            try:
                fallback_profile = self._fetch(self.fallback, instrument.asset_type, code)
                if fallback_profile:
                    sources.append(getattr(self.fallback, "name", self.fallback.__class__.__name__))
            except Exception as exc:
                errors.append(exc)

        merged = dict(fallback_profile)
        merged.update({key: value for key, value in primary_profile.items() if not _missing(value)})
        if merged:
            availability = Availability(status="available")
        else:
            provider_failure = any(isinstance(error, ProviderError) for error in errors)
            reason = "上游数据源暂时无法提供资料" if provider_failure else "当前数据源没有返回资料"
            availability = Availability(status="unavailable", reason=reason)

        if instrument.asset_type == "etf":
            profile = AssetProfile(code=code, asset_type="etf", etf=EtfProfile(**merged, availability=availability))
        else:
            profile = AssetProfile(code=code, asset_type="equity", equity=EquityProfile(**merged, availability=availability))
        return profile, sources or self.provider_names[:1]

    def get_profile(self, code: str, market_bars=None, benchmark_bars=None) -> AssetProfile:
        code = normalize_code(code)
        with self._lock:
            cached = self._profile_cache.get(code)
            if cached and monotonic() - cached[0] < self.profile_ttl_seconds:
                profile = cached[1].model_copy(deep=True)
            else:
                instrument = self.get_instrument(code)
                profile, sources = self._base_profile(code, instrument)
                self._profile_cache[code] = (monotonic(), profile.model_copy(deep=True), sources)

        if profile.asset_type == "etf" and profile.etf:
            if profile.etf.nav is not None and market_bars:
                profile.etf.premium_rate = market_bars[-1].close / profile.etf.nav - 1
            if benchmark_bars and market_bars:
                asset_df = pd.DataFrame([bar.model_dump() for bar in market_bars]).set_index("trade_date")
                bench_df = pd.DataFrame([bar.model_dump() for bar in benchmark_bars]).set_index("trade_date")
                overlap = asset_df.join(bench_df, lsuffix="_asset", rsuffix="_bench", how="inner")
                if len(overlap) >= 20:
                    difference = (overlap["close_asset"].pct_change() - overlap["close_bench"].pct_change()).dropna()
                    profile.etf.tracking_deviation = difference.std(ddof=1) * np.sqrt(252)
        return profile

    def profile_sources(self, code: str) -> list[str]:
        cached = self._profile_cache.get(normalize_code(code))
        return list(cached[2]) if cached else self.provider_names[:1]
