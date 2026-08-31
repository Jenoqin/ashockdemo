import math
from datetime import date

import pandas as pd
import pytest

from quantlab.cache import MarketCache
from quantlab.providers.base import ProviderError
from quantlab.providers.tushare_provider import TushareProvider


class FakePro:
    def fund_adj(self, **kwargs):
        return pd.DataFrame([{"trade_date": "20260105", "adj_factor": 1.0}])

    def adj_factor(self, **kwargs):
        return pd.DataFrame([{"trade_date": "20260105", "adj_factor": 1.0}])

    def fund_daily(self, **kwargs):
        assert kwargs["ts_code"] == "512480.SH"
        return pd.DataFrame(
            [
                {
                    "ts_code": "512480.SH",
                    "trade_date": "20260105",
                    "open": 1.20,
                    "high": 1.26,
                    "low": 1.19,
                    "close": 1.25,
                    "vol": 100,
                    "amount": 125,
                }
            ]
        )

    def daily(self, **kwargs):
        assert kwargs["ts_code"] == "600519.SH"
        return pd.DataFrame(
            [
                {
                    "ts_code": "600519.SH",
                    "trade_date": "20260105",
                    "open": 1400.0,
                    "high": 1420.0,
                    "low": 1390.0,
                    "close": 1410.0,
                    "vol": 50,
                    "amount": 70500,
                }
            ]
        )


def test_tushare_without_token_reports_configuration_error():
    with pytest.raises(ProviderError, match="TUSHARE_TOKEN"):
        TushareProvider(None).get_daily(
            "512480.SH", date(2026, 1, 1), date(2026, 1, 6)
        )


def test_tushare_maps_etf_daily():
    row = TushareProvider(FakePro()).get_daily(
        "512480.SH", date(2026, 1, 1), date(2026, 1, 6)
    )[0]
    assert row.code == "512480.SH"
    assert row.trade_date == date(2026, 1, 5)
    assert (row.open, row.high, row.low, row.close) == (1.20, 1.26, 1.19, 1.25)


def test_tushare_uses_daily_endpoint_for_equity():
    row = TushareProvider(FakePro()).get_daily(
        "600519.SH", date(2026, 1, 1), date(2026, 1, 6)
    )[0]
    assert (row.code, row.close) == ("600519.SH", 1410.0)


def test_tushare_normalizes_hfq_price_and_amount_to_yuan():
    class AdjustedFakePro(FakePro):
        def adj_factor(self, **kwargs):
            return pd.DataFrame(
                [{"trade_date": "20260105", "adj_factor": 2.0}]
            )

    row = TushareProvider(AdjustedFakePro()).get_daily(
        "600519.SH", date(2026, 1, 1), date(2026, 1, 6)
    )[0]
    assert row.close == 2820.0
    assert row.amount == 70500000.0


def test_tushare_catalog_maps_formal_company_name():
    class CatalogFakePro:
        def stock_basic(self, **kwargs):
            assert "fullname" in kwargs["fields"]
            return pd.DataFrame(
                [
                    {
                        "ts_code": "600519.SH",
                        "symbol": "600519",
                        "name": "贵州茅台",
                        "fullname": "贵州茅台酒股份有限公司",
                    }
                ]
            )

        def etf_basic(self, **kwargs):
            return pd.DataFrame()

    provider = TushareProvider(CatalogFakePro())
    instrument = provider.get_instrument("600519.SH")
    assert instrument.name == "贵州茅台"
    assert instrument.full_name == "贵州茅台酒股份有限公司"
    assert [item.code for item in provider.search("贵州茅台酒股份有限公司")] == [
        "600519.SH"
    ]


def test_tushare_catalog_persists_and_loads_without_client(tmp_path):
    class CatalogFakePro:
        def stock_basic(self, **kwargs):
            return pd.DataFrame([{
                "ts_code": "600519.SH",
                "symbol": "600519",
                "name": "贵州茅台",
                "fullname": "贵州茅台酒股份有限公司",
                "industry": "食品饮料",
                "list_date": "20010827",
            }])

        def etf_basic(self, **kwargs):
            return pd.DataFrame()

    cache = MarketCache(tmp_path / "market.db")
    fetched = TushareProvider(CatalogFakePro(), cache)
    assert fetched.get_instrument("600519.SH").name == "贵州茅台"
    assert fetched.catalog_meta()["cache_hit"] is False

    restored = TushareProvider(None, cache)
    assert restored.get_instrument("600519.SH").full_name == "贵州茅台酒股份有限公司"
    assert restored.get_listing_date("600519.SH") == date(2001, 8, 27)
    assert restored.catalog_meta()["cache_hit"] is True
    assert restored.catalog_meta()["warnings"] == []


def test_stale_catalog_falls_back_when_provider_is_unavailable(tmp_path):
    class WorkingCatalog:
        def stock_basic(self, **kwargs):
            return pd.DataFrame([{
                "ts_code": "600519.SH",
                "name": "贵州茅台",
                "fullname": "贵州茅台酒股份有限公司",
                "list_date": "20010827",
            }])

        def etf_basic(self, **kwargs):
            return pd.DataFrame()

    class BrokenCatalog:
        def stock_basic(self, **kwargs):
            raise RuntimeError("upstream unavailable")

    cache = MarketCache(tmp_path / "market.db")
    TushareProvider(WorkingCatalog(), cache).get_instrument("600519.SH")

    restored = TushareProvider(BrokenCatalog(), cache)
    restored.catalog_ttl_seconds = 0
    assert restored.get_instrument("600519.SH").name == "贵州茅台"
    assert restored.catalog_meta()["cache_hit"] is True
    assert restored.catalog_meta()["warnings"] == ["STALE_CACHE"]


def test_tushare_maps_complete_trade_calendar_and_listing_date():
    class MetadataFakePro:
        def trade_cal(self, **kwargs):
            assert kwargs["exchange"] == "SSE"
            return pd.DataFrame([
                {"exchange": "SSE", "cal_date": "20260103", "is_open": 0},
                {"exchange": "SSE", "cal_date": "20260104", "is_open": 0},
                {"exchange": "SSE", "cal_date": "20260105", "is_open": 1},
            ])

        def stock_basic(self, **kwargs):
            return pd.DataFrame([{
                "ts_code": "600519.SH",
                "symbol": "600519",
                "name": "贵州茅台",
                "fullname": "贵州茅台酒股份有限公司",
                "list_date": "20010827",
            }])

        def etf_basic(self, **kwargs):
            return pd.DataFrame()

    provider = TushareProvider(MetadataFakePro())

    assert provider.get_trade_calendar(
        "SSE", date(2026, 1, 3), date(2026, 1, 5)
    ) == {
        date(2026, 1, 3): False,
        date(2026, 1, 4): False,
        date(2026, 1, 5): True,
    }
    assert provider.get_listing_date("600519.SH") == date(2001, 8, 27)


@pytest.mark.parametrize("kind", ["wrong_code", "out_of_range", "duplicate"])
def test_tushare_rejects_invalid_daily_identity_and_dates(kind):
    class InvalidDailyFakePro(FakePro):
        def daily(self, **kwargs):
            base = super().daily(**kwargs).iloc[0].to_dict()
            if kind == "wrong_code":
                base["ts_code"] = "000001.SZ"
                rows = [base]
            elif kind == "out_of_range":
                base["trade_date"] = "20260107"
                rows = [base]
            else:
                rows = [base, dict(base)]
            return pd.DataFrame(rows)

    with pytest.raises(ProviderError):
        TushareProvider(InvalidDailyFakePro()).get_daily(
            "600519.SH", date(2026, 1, 1), date(2026, 1, 6)
        )


def test_tushare_rejects_out_of_range_adjustment_factor():
    class InvalidFactorFakePro(FakePro):
        def adj_factor(self, **kwargs):
            return pd.DataFrame([
                {"trade_date": "20260105", "adj_factor": 1.0},
                {"trade_date": "20260107", "adj_factor": 1.0},
            ])

    with pytest.raises(ProviderError, match="复权因子包含区间外日期"):
        TushareProvider(InvalidFactorFakePro()).get_daily(
            "600519.SH", date(2026, 1, 1), date(2026, 1, 6)
        )


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("open", None),
        ("high", math.inf),
        ("low", 0),
        ("close", 1500),
        ("vol", -1),
        ("amount", math.inf),
    ],
)
def test_tushare_rejects_malformed_daily_numeric_values(field, value):
    class MalformedDailyFakePro(FakePro):
        def daily(self, **kwargs):
            row = super().daily(**kwargs).iloc[0].to_dict()
            row[field] = value
            return pd.DataFrame([row])

    with pytest.raises(ProviderError, match="行情响应无效"):
        TushareProvider(MalformedDailyFakePro()).get_daily(
            "600519.SH", date(2026, 1, 1), date(2026, 1, 6)
        )
