from datetime import date
from quantlab.cache import MarketCache
from quantlab.models import Instrument
from quantlab.providers.base import ProviderError
from quantlab.services.assets import AssetService

class FakeProfileProvider:
    name = "Tushare Pro"

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


def test_profile_provenance_uses_only_tushare():
    service = AssetService(FakeProfileProvider())
    service.get_profile("600519.SH")
    assert service.profile_sources("600519.SH") == ["Tushare Pro"]


def test_profile_persists_and_survives_service_restart_without_provider(tmp_path):
    cache = MarketCache(tmp_path / "market.db")
    first = AssetService(FakeProfileProvider(), cache)
    expected = first.get_profile("512480.SH")
    assert first.profile_meta("512480.SH")["cache_hit"] is False

    class OfflineProvider(FakeProfileProvider):
        def get_instrument(self, code):
            raise ProviderError(self.name, code, "offline")

        def get_etf_profile(self, code):
            raise AssertionError("fresh SQLite profile should bypass provider")

    restored = AssetService(OfflineProvider(), cache)
    assert restored.get_profile("512480.SH") == expected
    assert restored.profile_meta("512480.SH")["cache_hit"] is True
    assert restored.profile_meta("512480.SH")["warnings"] == []


def test_stale_profile_is_served_when_refresh_fails(tmp_path):
    cache = MarketCache(tmp_path / "market.db")
    expected = AssetService(FakeProfileProvider(), cache).get_profile("512480.SH")

    class BrokenProfileProvider(FakeProfileProvider):
        profile_calls = 0

        def get_etf_profile(self, code):
            self.profile_calls += 1
            raise ProviderError(self.name, code, "offline")

    provider = BrokenProfileProvider()
    restored = AssetService(provider, cache)
    restored.profile_ttl_seconds = 0
    assert restored.get_profile("512480.SH") == expected
    assert restored.profile_meta("512480.SH")["cache_hit"] is True
    assert restored.profile_meta("512480.SH")["warnings"] == ["STALE_CACHE"]
    assert restored.get_profile("512480.SH") == expected
    assert provider.profile_calls == 1
