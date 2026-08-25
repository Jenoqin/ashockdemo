from datetime import date, timedelta, timezone, datetime
import random
from typing import Dict, Any

from quantlab.models import Instrument, PriceBar
from quantlab.errors import InstrumentNotFoundError
from quantlab.providers.base import normalize_code

class DemoProvider:
    name = "Demo"
    anchor_date = date(2000, 1, 3)

    _INSTRUMENTS = {
        "510300.SH": Instrument(code="510300.SH", name="沪深300ETF", asset_type="etf", exchange="SH"),
        "512480.SH": Instrument(code="512480.SH", name="半导体ETF", asset_type="etf", exchange="SH"),
        "600519.SH": Instrument(code="600519.SH", name="贵州茅台", asset_type="equity", exchange="SH"),
    }

    def __init__(self):
        pass

    def search(self, query: str) -> list[Instrument]:
        value = query.strip().upper()
        if not value:
            return []
        return [
            instrument
            for instrument in self._INSTRUMENTS.values()
            if value in instrument.code or value in instrument.name.upper()
        ]

    def get_instrument(self, code: str) -> Instrument:
        code = normalize_code(code)
        instrument = self._INSTRUMENTS.get(code)
        if instrument is None:
            raise InstrumentNotFoundError(code)
        return instrument

    def get_daily(self, code: str, start: date, end: date) -> list[PriceBar]:
        code = normalize_code(code)
        bars = []
        current = self.anchor_date
        price = 1.0 if "51" in code else 1500.0
        rng = random.Random(int(code.split(".")[0]))

        while current <= end:
            if current.weekday() < 5:  # Monday to Friday
                change = rng.uniform(-0.02, 0.02)
                price = price * (1 + change)
                open_price = price * rng.uniform(0.99, 1.01)
                high_price = max(price, open_price) * rng.uniform(1.0, 1.02)
                low_price = min(price, open_price) * rng.uniform(0.98, 1.0)
                volume = rng.uniform(1e6, 1e7)
                amount = rng.uniform(1e7, 1e8)
                if current >= start:
                    bars.append(PriceBar(
                        code=code,
                        trade_date=current,
                        open=open_price,
                        high=high_price,
                        low=low_price,
                        close=price,
                        volume=volume,
                        amount=amount,
                        source=self.name,
                        fetched_at=datetime.now(timezone.utc)
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
