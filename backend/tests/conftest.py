from datetime import date
import pytest
from fastapi.testclient import TestClient
from quantlab.main import create_app
from quantlab.models import Instrument, PriceBar
from quantlab.cache import MarketCache
from quantlab.services.market_data import MarketDataService
from quantlab.services.assets import AssetService
from quantlab.services.backtest import BacktestService
from quantlab.api.dependencies import get_market_data_service, get_asset_service, get_backtest_service

class FullFakeProvider:
    name = "fake"

    def __init__(self):
        self.profile_calls = 0
    
    def search(self, query):
        if "512480" in query:
            return [Instrument(code="512480.SH", name="半导体 ETF", asset_type="etf", exchange="SH")]
        return []

    def get_instrument(self, code):
        if code == "512480.SH":
            return Instrument(code=code, name="半导体 ETF", asset_type="etf", exchange="SH")
        return Instrument(
            code=code,
            name="贵州茅台",
            full_name="贵州茅台酒股份有限公司",
            asset_type="equity",
            exchange="SH",
        )

    def get_daily(self, code, start, end):
        from datetime import datetime, timedelta, timezone
        fetched = datetime(2026, 8, 8, tzinfo=timezone.utc)
        return [
            PriceBar(
                code=code, trade_date=start + timedelta(days=i),
                open=1.0 + (start + timedelta(days=i) - date(2025, 1, 1)).days * 0.001,
                high=1.05 + (start + timedelta(days=i) - date(2025, 1, 1)).days * 0.001,
                low=0.95 + (start + timedelta(days=i) - date(2025, 1, 1)).days * 0.001,
                close=1.0 + (start + timedelta(days=i) - date(2025, 1, 1)).days * 0.001,
                volume=1000, source="fake", fetched_at=fetched
            )
            for i in range((end - start).days + 1)
        ]

    def get_index_daily(self, code, start, end):
        from datetime import datetime, timedelta, timezone
        fetched = datetime(2026, 8, 8, tzinfo=timezone.utc)
        return [
            PriceBar(
                code=code,
                trade_date=start + timedelta(days=i),
                open=1000 + i,
                high=1010 + i,
                low=990 + i,
                close=1000 + i,
                volume=1000,
                source="fake",
                fetched_at=fetched,
            )
            for i in range((end - start).days + 1)
        ]

    def get_trade_calendar(self, exchange, start, end):
        from datetime import timedelta
        return {
            start + timedelta(days=i): True
            for i in range((end - start).days + 1)
        }

    def get_listing_date(self, code):
        return date(2000, 1, 1)

    def get_tracking_index_code(self, code):
        return "H30184.CSI" if code == "512480.SH" else None

    def get_etf_profile(self, code):
        self.profile_calls += 1
        return {"tracking_index": "中证全指半导体产品与设备指数", "holdings": [{"name": "样本公司", "weight": 0.10}]}

    def get_equity_profile(self, code):
        return {"industry": "食品饮料", "financial_periods": [{"report_date": date(2026, 3, 31), "revenue": 1.0, "net_profit": 0.5}]}

@pytest.fixture
def client(tmp_path):
    fake = FullFakeProvider()
    cache = MarketCache(tmp_path / "market.db")
    market = MarketDataService(cache, fake)
    asset = AssetService(fake)
    backtest = BacktestService()

    app = create_app()
    app.dependency_overrides[get_market_data_service] = lambda: market
    app.dependency_overrides[get_asset_service] = lambda: asset
    app.dependency_overrides[get_backtest_service] = lambda: backtest
    app.state.fake_provider = fake
    return TestClient(app)
