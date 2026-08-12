from datetime import date, timedelta
import random
from typing import Dict, Any

from quantlab.models import Instrument, PriceBar
from quantlab.providers.base import ProviderError, normalize_code

class DemoProvider:
    name = "Demo"

    def __init__(self):
        pass

    def search(self, query: str) -> list[Instrument]:
        return [
            Instrument(code="510300.SH", name="沪深300ETF", asset_type="etf", exchange="SH"),
            Instrument(code="512480.SH", name="半导体ETF", asset_type="etf", exchange="SH"),
            Instrument(code="600519.SH", name="贵州茅台", asset_type="equity", exchange="SH")
        ]

    def get_instrument(self, code: str) -> Instrument:
        code = normalize_code(code)
        if "510300" in code:
            return Instrument(code="510300.SH", name="沪深300ETF", asset_type="etf", exchange="SH")
        if "512480" in code:
            return Instrument(code="512480.SH", name="半导体ETF", asset_type="etf", exchange="SH")
        return Instrument(code="600519.SH", name="贵州茅台", asset_type="equity", exchange="SH")

    def get_daily(self, code: str, start: date, end: date) -> list[PriceBar]:
        code = normalize_code(code)
        bars = []
        current = start
        price = 1.0 if "51" in code else 1500.0
        random.seed(int(code.split(".")[0]))  # Deterministic random

        while current <= end:
            if current.weekday() < 5:  # Monday to Friday
                change = random.uniform(-0.02, 0.02)
                price = price * (1 + change)
                bars.append(PriceBar(
                    code=code,
                    trade_date=current,
                    open=price * random.uniform(0.99, 1.01),
                    high=price * random.uniform(1.0, 1.02),
                    low=price * random.uniform(0.98, 1.0),
                    close=price,
                    volume=random.uniform(1e6, 1e7),
                    amount=random.uniform(1e7, 1e8),
                    source=self.name,
                    fetched_at=date.today().isoformat()
                ))
            current += timedelta(days=1)
        return bars

    def get_etf_profile(self, code: str) -> Dict[str, Any]:
        return {
            "tracking_index": "演示指数",
            "tracking_index_code": "DEMO.CSI",
            "manager": "演示基金",
            "inception_date": "2020-01-01",
            "size": 5000000000,
            "shares": 4000000000,
            "nav": 1.25,
            "holdings": [{"name": "权重股1", "weight": 0.1, "code": "600000.SH"}]
        }

    def get_equity_profile(self, code: str) -> Dict[str, Any]:
        return {
            "industry": "演示行业",
            "valuation_trade_date": "2026-01-01",
            "pe": 15.0,
            "pb": 2.5,
            "total_market_cap": 200000000000,
            "float_market_cap": 100000000000,
            "financial_periods": []
        }
