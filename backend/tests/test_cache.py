from datetime import date, datetime, timezone
import sqlite3
from quantlab.cache import MarketCache
from quantlab.models import PriceBar
from quantlab.providers.base import normalize_code

def bar(day: int, close: float) -> PriceBar:
    return PriceBar(
        code="512480.SH", trade_date=date(2026, 1, day),
        open=close, high=close + 0.02, low=close - 0.02,
        close=close, volume=1000, amount=1284,
        source="akshare", fetched_at="2026-08-08T00:00:00Z",
    )

def test_normalize_code_understands_shanghai_etf_and_stock():
    assert normalize_code("512480") == "512480.SH"
    assert normalize_code("600519.SH") == "600519.SH"

def test_cache_upserts_and_returns_sorted_bars(tmp_path):
    cache = MarketCache(tmp_path / "test.db")
    cache.upsert_bars("akshare", [bar(3, 1.30), bar(2, 1.28), bar(3, 1.31)])
    rows = cache.get_bars("akshare", "512480.SH", date(2026, 1, 1), date(2026, 1, 3))
    assert [(row.trade_date.day, row.close) for row in rows] == [(2, 1.28), (3, 1.31)]

def test_cache_creates_missing_parent_directory(tmp_path):
    db_path = tmp_path / "nested" / "cache" / "test.db"
    MarketCache(db_path)
    assert db_path.is_file()

def test_missing_ranges_subtracts_synced_intervals(tmp_path):
    cache = MarketCache(tmp_path / "test.db")
    cache.mark_synced("akshare", "512480.SH", date(2026, 1, 3), date(2026, 1, 7))
    assert cache.missing_ranges("akshare", "512480.SH", date(2026, 1, 1), date(2026, 1, 10)) == [
        (date(2026, 1, 1), date(2026, 1, 2)),
        (date(2026, 1, 8), date(2026, 1, 10)),
    ]


def test_cache_reports_covered_days_and_provider_cooldown(tmp_path):
    cache = MarketCache(tmp_path / "test.db")
    cache.mark_synced("tushare", "512480.SH", date(2026, 1, 3), date(2026, 1, 7))
    cache.mark_synced("tushare", "512480.SH", date(2026, 1, 8), date(2026, 1, 9))

    assert cache.coverage_days("tushare", "512480.SH", date(2026, 1, 1), date(2026, 1, 10)) == 7
    assert cache.provider_in_cooldown("512480.SH", "tushare") is False

    cooldown_until = cache.record_provider_failure("512480.SH", "tushare")
    assert cooldown_until > datetime.now(timezone.utc)
    assert cache.provider_in_cooldown("512480.SH", "tushare") is True

    cache.record_provider_success("512480.SH", "tushare")
    assert cache.provider_in_cooldown("512480.SH", "tushare") is False
    assert cache.get_preferred_provider("512480.SH") == "tushare"


def test_cache_keeps_provider_datasets_separate(tmp_path):
    cache = MarketCache(tmp_path / "test.db")
    cache.upsert_bars("akshare", [bar(2, 1.28)])
    tushare_bar = bar(2, 4.18).model_copy(update={"source": "tushare"})
    cache.upsert_bars("tushare", [tushare_bar])

    akshare = cache.get_bars("akshare", "512480.SH", date(2026, 1, 1), date(2026, 1, 3))
    tushare = cache.get_bars("tushare", "512480.SH", date(2026, 1, 1), date(2026, 1, 3))

    assert [row.close for row in akshare] == [1.28]
    assert [row.close for row in tushare] == [4.18]


def test_legacy_migration_separates_sources_and_invalidates_sync_ranges(tmp_path):
    db_path = tmp_path / "legacy.db"
    with sqlite3.connect(db_path) as conn:
        conn.execute("""
            CREATE TABLE price_bars (
                code TEXT, trade_date TEXT, open REAL, high REAL, low REAL,
                close REAL, volume REAL, amount REAL, source TEXT,
                fetched_at TEXT, PRIMARY KEY (code, trade_date)
            )
        """)
        conn.execute("""
            INSERT INTO price_bars VALUES (
                '512480.SH', '2026-01-02', 1.0, 1.1, 0.9, 1.0,
                1000, 1000, 'Demo', '2026-08-08T00:00:00Z'
            )
        """)
        conn.execute("""
            CREATE TABLE sync_ranges (
                code TEXT, start_date TEXT, end_date TEXT,
                PRIMARY KEY (code, start_date, end_date)
            )
        """)
        conn.execute("""
            INSERT INTO sync_ranges VALUES (
                '512480.SH', '2026-01-01', '2026-01-31'
            )
        """)

    cache = MarketCache(db_path)

    assert len(cache.get_bars("Demo", "512480.SH", date(2026, 1, 1), date(2026, 1, 31))) == 1
    assert cache.missing_ranges("Demo", "512480.SH", date(2026, 1, 1), date(2026, 1, 31)) == [
        (date(2026, 1, 1), date(2026, 1, 31))
    ]
