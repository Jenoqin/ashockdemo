from datetime import date, datetime, timezone
from typing import List, Optional
from pydantic import BaseModel
from quantlab.models import PriceBar, ResponseMeta
from quantlab.cache import MarketCache
from quantlab.providers.base import MarketDataProvider, ProviderError, normalize_code
from quantlab.errors import DataUnavailableError
from quantlab.services.quality import validate_bars

class MarketDataResult(BaseModel):
    bars: List[PriceBar]
    meta: ResponseMeta

class MarketDataService:
    def __init__(self, cache: MarketCache, primary: MarketDataProvider, fallback: Optional[MarketDataProvider] = None):
        self.cache = cache
        self.primary = primary
        self.fallback = fallback

    def get_daily(self, code: str, start: date, end: date, refresh: bool = False) -> MarketDataResult:
        code = normalize_code(code)
        warnings = []
        sources = []
        is_cache_hit = False
        
        if refresh:
            ranges = [(start, end)]
        else:
            ranges = self.cache.missing_ranges(code, start, end)
            
        fetched_bars = []
        successful_ranges = []
        primary_failed = False
        
        for r_start, r_end in ranges:
            try:
                new_bars = self.primary.get_daily(code, r_start, r_end)
                if not new_bars:
                    raise ProviderError(self.primary.name, code, "Empty response")
                val_warnings = validate_bars(new_bars)
                fatal = any(w.startswith("INVALID_OHLC") or w.startswith("DUPLICATE") for w in val_warnings)
                if fatal:
                    raise ProviderError(self.primary.name, code, "Fatal validation errors")
                fetched_bars.extend(new_bars)
                sources.append(self.primary.name)
                successful_ranges.append((r_start, r_end))
            except ProviderError:
                primary_failed = True
                warnings.append("PRIMARY_PROVIDER_FAILED")
                
                if self.fallback:
                    try:
                        fb_bars = self.fallback.get_daily(code, r_start, r_end)
                        if not fb_bars:
                            raise ProviderError(self.fallback.name, code, "Empty response")
                        fb_val_warnings = validate_bars(fb_bars)
                        fb_fatal = any(w.startswith("INVALID_OHLC") or w.startswith("DUPLICATE") for w in fb_val_warnings)
                        if fb_fatal:
                            raise ProviderError(self.fallback.name, code, "Fatal validation errors in fallback")
                        fetched_bars.extend(fb_bars)
                        sources.append(self.fallback.name)
                        successful_ranges.append((r_start, r_end))
                        primary_failed = False
                    except ProviderError:
                        pass
        
        if fetched_bars:
            self.cache.upsert_bars(fetched_bars)
            for r_start, r_end in successful_ranges:
                self.cache.mark_synced(code, r_start, r_end)
        
        if refresh and self.fallback and not primary_failed:
            try:
                primary_last20 = sorted([b for b in fetched_bars if b.source == self.primary.name], key=lambda x: x.trade_date)[-20:]
                if primary_last20:
                    fb_bars = self.fallback.get_daily(code, primary_last20[0].trade_date, primary_last20[-1].trade_date)
                    fb_dict = {b.trade_date: b for b in fb_bars}
                    for pb in primary_last20:
                        if pb.trade_date in fb_dict:
                            fb = fb_dict[pb.trade_date]
                            close_diff = abs(pb.close - fb.close)
                            if close_diff > max(0.001, pb.close * 0.001):
                                warnings.append(f"SOURCE_DIFFERENCE:{pb.trade_date.isoformat()}:close")
                            vol_diff = abs(pb.volume - fb.volume)
                            if pb.volume > 0 and vol_diff / pb.volume > 0.05:
                                warnings.append(f"SOURCE_DIFFERENCE:{pb.trade_date.isoformat()}:volume")
            except ProviderError:
                pass

        cached = self.cache.get_bars(code, start, end)
        if not cached:
            raise DataUnavailableError(code, 2 if self.fallback else 1)
            
        if primary_failed and not fetched_bars:
            warnings.append("STALE_CACHE")
            is_cache_hit = True
        elif not refresh and not ranges:
            is_cache_hit = True
            
        sources = list(set(sources))
        if not sources:
            sources = ["cache"]
            
        return MarketDataResult(
            bars=cached,
            meta=ResponseMeta(
                sources=sources,
                fetched_at=datetime.now(timezone.utc),
                cache_hit=is_cache_hit,
                is_demo=self.primary.name.lower() == "demo",
                warnings=warnings
            )
        )
