from datetime import date
import numpy as np
import pandas as pd
from typing import Any
from quantlab.models import AssetProfile, EtfProfile, EquityProfile, Availability, Instrument, Holding, FinancialPeriod

class AssetService:
    def __init__(self, provider: Any):
        self.provider = provider

    def get_profile(self, code: str, market_bars=None, benchmark_bars=None) -> AssetProfile:
        instrument = self.provider.get_instrument(code)

        if instrument.asset_type == "etf":
            get_etf = getattr(self.provider, "get_etf_profile", None)
            if get_etf:
                try:
                    etf_dict = get_etf(code)
                    availability = Availability(status="available")
                except Exception as e:
                    availability = Availability(status="unavailable", reason="当前数据源权限不足")
                    etf_dict = {}
            else:
                availability = Availability(status="unavailable", reason="当前数据源权限不足")
                etf_dict = {}
            
            derived = {}
            if etf_dict.get("nav") is not None and market_bars and len(market_bars) > 0:
                last_bar = market_bars[-1]
                derived["premium_rate"] = (last_bar.close / etf_dict["nav"]) - 1
            
            # tracking deviation
            if benchmark_bars and market_bars:
                asset_df = pd.DataFrame([b.model_dump() for b in market_bars]).set_index("trade_date")
                bench_df = pd.DataFrame([b.model_dump() for b in benchmark_bars]).set_index("trade_date")
                overlap = asset_df.join(bench_df, lsuffix="_asset", rsuffix="_bench", how="inner")
                if len(overlap) >= 20:
                    asset_ret = overlap["close_asset"].pct_change()
                    bench_ret = overlap["close_bench"].pct_change()
                    diff = (asset_ret - bench_ret).dropna()
                    derived["tracking_deviation"] = diff.std(ddof=1) * np.sqrt(252)

            etf_profile = EtfProfile(**etf_dict, **derived, availability=availability)
            return AssetProfile(code=code, asset_type=instrument.asset_type, etf=etf_profile)
        else:
            get_eq = getattr(self.provider, "get_equity_profile", None)
            if get_eq:
                try:
                    eq_dict = get_eq(code)
                    availability = Availability(status="available")
                except Exception as e:
                    availability = Availability(status="unavailable", reason="当前数据源权限不足")
                    eq_dict = {}
            else:
                availability = Availability(status="unavailable", reason="当前数据源权限不足")
                eq_dict = {}
            
            eq_profile = EquityProfile(**eq_dict, availability=availability)
            return AssetProfile(code=code, asset_type=instrument.asset_type, equity=eq_profile)
