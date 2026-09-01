from __future__ import annotations

from datetime import datetime, timezone
from queue import Empty, Queue
import sqlite3
from threading import Lock, Thread
from time import monotonic
from typing import Any

import numpy as np
import pandas as pd

from quantlab.models import AssetProfile, Availability, EquityProfile, EtfProfile, Instrument
from quantlab.providers.base import ProviderError, normalize_code


class AssetService:
    profile_ttl_seconds = 10 * 60
    stale_profile_retry_seconds = 60
    provider_timeout_seconds = 6
    provider_cooldown_seconds = 60

    def __init__(self, provider: Any, cache=None):
        self.provider = provider
        self.cache = cache
        self._profile_cache: dict[
            str, tuple[datetime, AssetProfile, list[str]]
        ] = {}
        self._profile_response_meta: dict[str, dict[str, Any]] = {}
        self._profile_retry_after: dict[str, float] = {}
        self._lock = Lock()
        self._provider_slow_until = 0.0

    @staticmethod
    def _age_seconds(fetched_at: datetime) -> float:
        if fetched_at.tzinfo is None:
            fetched_at = fetched_at.replace(tzinfo=timezone.utc)
        return max(0.0, (datetime.now(timezone.utc) - fetched_at).total_seconds())

    @staticmethod
    def _is_available(profile: AssetProfile) -> bool:
        availability = (
            profile.etf.availability
            if profile.asset_type == "etf" and profile.etf
            else profile.equity.availability
            if profile.asset_type == "equity" and profile.equity
            else None
        )
        return availability is not None and availability.status == "available"

    def _set_profile_meta(
        self,
        code: str,
        sources: list[str],
        fetched_at: datetime,
        *,
        cache_hit: bool,
        warnings: list[str] | None = None,
    ) -> None:
        self._profile_response_meta[code] = {
            "sources": list(sources),
            "fetched_at": fetched_at,
            "cache_hit": cache_hit,
            "warnings": list(warnings or []),
        }

    def _provider_call(self, operation, code: str):
        if monotonic() < self._provider_slow_until:
            raise ProviderError(getattr(self.provider, "name", "provider"), code, "数据源冷却中")
        result: Queue = Queue(maxsize=1)

        def run() -> None:
            try:
                result.put((True, operation()))
            except Exception as exc:
                result.put((False, exc))

        worker = Thread(target=run, daemon=True)
        worker.start()
        try:
            succeeded, value = result.get(timeout=self.provider_timeout_seconds)
        except Empty as exc:
            self._provider_slow_until = monotonic() + self.provider_cooldown_seconds
            raise ProviderError(getattr(self.provider, "name", "provider"), code, "数据源响应超时") from exc
        if not succeeded:
            raise value
        self._provider_slow_until = 0.0
        return value

    @property
    def provider_names(self) -> list[str]:
        return [getattr(self.provider, "name", self.provider.__class__.__name__)]

    def search(self, query: str) -> list[Instrument]:
        try:
            results = self._provider_call(lambda: self.provider.search(query), query)
            if results:
                return results
        except (ProviderError, LookupError):
            pass
        return []

    def get_instrument_with_meta(
        self, code: str
    ) -> tuple[Instrument, dict[str, Any]]:
        code = normalize_code(code)
        try:
            instrument = self._provider_call(
                lambda: self.provider.get_instrument(code), code
            )
        except ProviderError:
            cached = (
                self.cache.get_instrument_catalog(self.provider_names[0])
                if self.cache
                else None
            )
            if cached:
                entries, fetched_at = cached
                instrument = next(
                    (
                        item
                        for item, _metadata in entries
                        if item.code == code
                    ),
                    None,
                )
                if instrument is not None:
                    return instrument, {
                        "sources": self.provider_names[:1],
                        "fetched_at": fetched_at,
                        "cache_hit": True,
                        "warnings": ["STALE_CACHE"],
                    }
            raise
        return instrument, self.catalog_meta()

    def get_instrument(self, code: str) -> Instrument:
        instrument, _meta = self.get_instrument_with_meta(code)
        return instrument

    def get_tracking_index_code(self, code: str) -> str | None:
        """Load only ETF benchmark metadata; avoid the heavyweight profile APIs."""
        code = normalize_code(code)
        method = getattr(self.provider, "get_tracking_index_code", None)
        if method is None:
            return None
        value = self._provider_call(lambda: method(code), code)
        return str(value).upper() if value else None

    def _fetch(self, provider: Any, asset_type: str, code: str) -> dict[str, Any]:
        method_name = "get_etf_profile" if asset_type == "etf" else "get_equity_profile"
        method = getattr(provider, method_name, None)
        if method is None:
            return {}
        return method(code) or {}

    def _base_profile(self, code: str, instrument: Instrument) -> tuple[AssetProfile, list[str]]:
        provider_profile: dict[str, Any] = {}
        errors: list[Exception] = []
        sources: list[str] = []
        try:
            provider_profile = self._provider_call(
                lambda: self._fetch(self.provider, instrument.asset_type, code), code
            )
            if provider_profile:
                sources.append(getattr(self.provider, "name", self.provider.__class__.__name__))
        except Exception as exc:
            errors.append(exc)

        if provider_profile:
            availability = Availability(status="available")
        else:
            provider_failure = any(isinstance(error, ProviderError) for error in errors)
            reason = "上游数据源暂时无法提供资料" if provider_failure else "当前数据源没有返回资料"
            availability = Availability(status="unavailable", reason=reason)

        if instrument.asset_type == "etf":
            profile = AssetProfile(
                code=code,
                asset_type="etf",
                etf=EtfProfile(**provider_profile, availability=availability),
            )
        else:
            profile = AssetProfile(
                code=code,
                asset_type="equity",
                equity=EquityProfile(**provider_profile, availability=availability),
            )
        return profile, sources or self.provider_names[:1]

    def get_profile(self, code: str, market_bars=None, benchmark_bars=None) -> AssetProfile:
        code = normalize_code(code)
        with self._lock:
            cached = self._profile_cache.get(code)
            if cached is None and self.cache:
                stored = self.cache.get_asset_profile(self.provider_names[0], code)
                if stored:
                    stored_profile, stored_at = stored
                    cached = (stored_at, stored_profile, self.provider_names[:1])
                    self._profile_cache[code] = cached

            cache_is_fresh = (
                cached is not None
                and self._age_seconds(cached[0]) < self.profile_ttl_seconds
            )
            stale_retry_is_active = (
                cached is not None
                and monotonic() < self._profile_retry_after.get(code, 0.0)
            )
            if cache_is_fresh or stale_retry_is_active:
                fetched_at, cached_profile, sources = cached
                profile = cached_profile.model_copy(deep=True)
                self._set_profile_meta(
                    code,
                    sources,
                    fetched_at,
                    cache_hit=True,
                    warnings=["STALE_CACHE"] if stale_retry_is_active else [],
                )
            else:
                stale = cached
                try:
                    instrument = self.get_instrument(code)
                except (ProviderError, LookupError):
                    if stale is None:
                        raise
                    fetched_at, cached_profile, sources = stale
                    profile = cached_profile.model_copy(deep=True)
                    self._set_profile_meta(
                        code,
                        sources,
                        fetched_at,
                        cache_hit=True,
                        warnings=["STALE_CACHE"],
                    )
                    self._profile_retry_after[code] = (
                        monotonic() + self.stale_profile_retry_seconds
                    )
                else:
                    fetched_profile, sources = self._base_profile(code, instrument)
                    if not self._is_available(fetched_profile) and stale is not None:
                        fetched_at, cached_profile, sources = stale
                        profile = cached_profile.model_copy(deep=True)
                        self._set_profile_meta(
                            code,
                            sources,
                            fetched_at,
                            cache_hit=True,
                            warnings=["STALE_CACHE"],
                        )
                        self._profile_retry_after[code] = (
                            monotonic() + self.stale_profile_retry_seconds
                        )
                    else:
                        fetched_at = datetime.now(timezone.utc)
                        profile = fetched_profile
                        warnings: list[str] = []
                        if self._is_available(profile) and self.cache:
                            try:
                                self.cache.upsert_asset_profile(
                                    self.provider_names[0], profile, fetched_at
                                )
                            except (sqlite3.Error, ValueError):
                                warnings.append("CACHE_WRITE_FAILED")
                        self._profile_cache[code] = (
                            fetched_at,
                            profile.model_copy(deep=True),
                            sources,
                        )
                        self._profile_retry_after.pop(code, None)
                        self._set_profile_meta(
                            code,
                            sources,
                            fetched_at,
                            cache_hit=False,
                            warnings=warnings,
                        )

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
        code = normalize_code(code)
        meta = self._profile_response_meta.get(code)
        if meta:
            return list(meta["sources"])
        cached = self._profile_cache.get(code)
        return list(cached[2]) if cached else self.provider_names[:1]

    def profile_meta(self, code: str) -> dict[str, Any]:
        code = normalize_code(code)
        return self._profile_response_meta.get(code, {
            "sources": self.provider_names[:1],
            "fetched_at": datetime.now(timezone.utc),
            "cache_hit": False,
            "warnings": [],
        })

    def catalog_meta(self) -> dict[str, Any]:
        get_meta = getattr(self.provider, "catalog_meta", None)
        if callable(get_meta):
            return get_meta()
        return {
            "sources": self.provider_names[:1],
            "fetched_at": datetime.now(timezone.utc),
            "cache_hit": False,
            "warnings": [],
        }
