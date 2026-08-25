from datetime import date
import pandas as pd
from quantlab.providers.akshare_provider import AkShareProvider
from quantlab.providers.demo_provider import DemoProvider
from quantlab.providers.tushare_provider import TushareProvider
from quantlab.cache import MarketCache
from quantlab.services.market_data import MarketDataService

class FakeAk:
    def stock_info_a_code_name(self):
        return pd.DataFrame([{"code": "600519", "name": "贵州茅台"}])

    def fund_etf_spot_em(self):
        return pd.DataFrame([{"代码": "512480", "名称": "半导体ETF"}])

    def fund_etf_category_sina(self, **kwargs):
        return pd.DataFrame([{"代码": "512480", "名称": "半导体ETF"}])

    def fund_etf_hist_em(self, **kwargs):
        assert kwargs["symbol"] == "512480"
        return pd.DataFrame([{
            "日期": "2026-01-05", "开盘": 1.20, "收盘": 1.25,
            "最高": 1.26, "最低": 1.19, "成交量": 100, "成交额": 125,
        }])

    def stock_zh_a_hist(self, **kwargs):
        assert kwargs["symbol"] == "600519"
        return pd.DataFrame([{
            "日期": "2026-01-05", "开盘": 1400.0, "收盘": 1410.0,
            "最高": 1420.0, "最低": 1390.0, "成交量": 50, "成交额": 70500,
        }])

class FakePro:
    def fund_adj(self, **kwargs):
        return pd.DataFrame([{"trade_date": "20260105", "adj_factor": 1.0}])

    def adj_factor(self, **kwargs):
        return pd.DataFrame([{"trade_date": "20260105", "adj_factor": 1.0}])

    def fund_daily(self, **kwargs):
        assert kwargs["ts_code"] == "512480.SH"
        return pd.DataFrame([{
            "ts_code": "512480.SH", "trade_date": "20260105",
            "open": 1.20, "high": 1.26, "low": 1.19, "close": 1.25,
            "vol": 100, "amount": 125,
        }])

    def daily(self, **kwargs):
        assert kwargs["ts_code"] == "600519.SH"
        return pd.DataFrame([{
            "ts_code": "600519.SH", "trade_date": "20260105",
            "open": 1400.0, "high": 1420.0, "low": 1390.0, "close": 1410.0,
            "vol": 50, "amount": 70500,
        }])

def assert_etf_bar(row):
    assert row.code == "512480.SH"
    assert row.trade_date == date(2026, 1, 5)
    assert (row.open, row.high, row.low, row.close) == (1.20, 1.26, 1.19, 1.25)

def test_akshare_maps_etf_daily():
    assert_etf_bar(AkShareProvider(FakeAk()).get_daily("512480.SH", date(2026, 1, 1), date(2026, 1, 6))[0])

def test_tushare_maps_etf_daily():
    assert_etf_bar(TushareProvider(FakePro()).get_daily("512480.SH", date(2026, 1, 1), date(2026, 1, 6))[0])

def test_akshare_uses_stock_endpoint_for_equity():
    row = AkShareProvider(FakeAk()).get_daily("600519.SH", date(2026, 1, 1), date(2026, 1, 6))[0]
    assert (row.code, row.close) == ("600519.SH", 1410.0)

def test_tushare_uses_daily_endpoint_for_equity():
    row = TushareProvider(FakePro()).get_daily("600519.SH", date(2026, 1, 1), date(2026, 1, 6))[0]
    assert (row.code, row.close) == ("600519.SH", 1410.0)

def test_tushare_normalizes_hfq_price_and_amount_to_yuan():
    class AdjustedFakePro(FakePro):
        def adj_factor(self, **kwargs):
            return pd.DataFrame([{"trade_date": "20260105", "adj_factor": 2.0}])

    row = TushareProvider(AdjustedFakePro()).get_daily("600519.SH", date(2026, 1, 1), date(2026, 1, 6))[0]
    assert row.close == 2820.0
    assert row.amount == 70500000.0

def test_demo_search_filters_and_unknown_code_is_rejected():
    provider = DemoProvider()
    assert [item.code for item in provider.search("贵州茅台")] == ["600519.SH"]
    assert provider.search("不存在") == []
    import pytest
    with pytest.raises(LookupError):
        provider.get_instrument("000001.SZ")

def test_akshare_catalog_search_returns_real_catalog_entries():
    provider = AkShareProvider(FakeAk())
    assert [item.code for item in provider.search("贵州茅台")] == ["600519.SH"]
    assert [item.code for item in provider.search("512480")] == ["512480.SH"]
    assert provider.search("不存在") == []

def test_demo_history_is_independent_of_requested_start_date():
    provider = DemoProvider()
    three_months = provider.get_daily("512480.SH", date(2026, 5, 26), date(2026, 8, 26))
    six_months = provider.get_daily("512480.SH", date(2026, 2, 26), date(2026, 8, 26))
    six_month_subset = [bar for bar in six_months if bar.trade_date >= date(2026, 5, 26)]
    assert [(bar.trade_date, bar.close) for bar in three_months] == [
        (bar.trade_date, bar.close) for bar in six_month_subset
    ]

def test_demo_cache_results_do_not_depend_on_query_order(tmp_path):
    def load_in_order(db_name, ranges):
        service = MarketDataService(MarketCache(tmp_path / db_name), DemoProvider())
        return {
            label: [(bar.trade_date, bar.close) for bar in service.get_daily("512480.SH", start, date(2026, 8, 26)).bars]
            for label, start in ranges
        }

    short_first = load_in_order("short-first.db", [
        ("3m", date(2026, 5, 26)),
        ("6m", date(2026, 2, 26)),
    ])
    long_first = load_in_order("long-first.db", [
        ("6m", date(2026, 2, 26)),
        ("3m", date(2026, 5, 26)),
    ])
    assert short_first == long_first
