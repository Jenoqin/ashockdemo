from datetime import date
import pandas as pd
from quantlab.providers.akshare_provider import AkShareProvider
from quantlab.providers.tushare_provider import TushareProvider

class FakeAk:
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
