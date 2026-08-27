from datetime import date
from quantlab.models import Instrument
from quantlab.services.assets import AssetService

class FakeProfileProvider:
    def get_instrument(self, code):
        if code == "512480.SH":
            return Instrument(code=code, name="半导体 ETF", asset_type="etf", exchange="SH")
        return Instrument(code=code, name="贵州茅台", asset_type="equity", exchange="SH")

    def get_etf_profile(self, code):
        return {"tracking_index": "中证全指半导体产品与设备指数", "holdings": [{"name": "样本公司", "weight": 0.10}]}

    def get_equity_profile(self, code):
        return {"industry": "食品饮料", "financial_periods": [{"report_date": date(2026, 3, 31), "revenue": 1.0, "net_profit": 0.5}]}

def test_etf_profile_contains_tracking_and_holdings():
    profile = AssetService(FakeProfileProvider()).get_profile("512480.SH")
    assert profile.asset_type == "etf"
    assert profile.etf.tracking_index
    assert profile.equity is None

def test_equity_profile_contains_report_dates():
    profile = AssetService(FakeProfileProvider()).get_profile("600519.SH")
    assert profile.asset_type == "equity"
    assert profile.equity.financial_periods[0].report_date
    assert profile.etf is None


class PrimaryPartialProvider(FakeProfileProvider):
    name = "AkShare"

    def get_equity_profile(self, code):
        return {"industry": "主源行业", "pe": None, "financial_periods": []}


class FallbackProfileProvider(FakeProfileProvider):
    name = "Tushare Pro"

    def get_equity_profile(self, code):
        return {
            "industry": "备用行业",
            "pe": 18.0,
            "pb": 2.0,
            "total_market_cap": 100.0,
            "financial_periods": [{"report_date": date(2026, 3, 31), "revenue": 1.0}],
        }


def test_profile_keeps_akshare_values_and_only_fills_missing_fields_from_tushare():
    service = AssetService(PrimaryPartialProvider(), FallbackProfileProvider())
    profile = service.get_profile("600519.SH")
    assert profile.equity.industry == "主源行业"
    assert profile.equity.pe == 18.0
    assert profile.equity.financial_periods[0].report_date == date(2026, 3, 31)
    assert service.profile_sources("600519.SH") == ["AkShare", "Tushare Pro"]


def test_instrument_fills_missing_formal_name_from_fallback():
    class Primary(FakeProfileProvider):
        name = "AkShare"

    class Fallback(FakeProfileProvider):
        name = "Tushare Pro"

        def get_instrument(self, code):
            return Instrument(
                code=code,
                name="贵州茅台",
                full_name="贵州茅台酒股份有限公司",
                asset_type="equity",
                exchange="SH",
            )

    instrument = AssetService(Primary(), Fallback()).get_instrument("600519.SH")
    assert instrument.full_name == "贵州茅台酒股份有限公司"
