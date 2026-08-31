from datetime import date, datetime, timezone
import sqlite3
from quantlab.cache import MarketCache
from quantlab.models import AssetProfile, Availability, EtfProfile, Instrument, PriceBar
from quantlab.providers.base import normalize_code

def bar(day: int, close: float) -> PriceBar:
    return PriceBar(
        code="512480.SH", trade_date=date(2026, 1, day),
        open=close, high=close + 0.02, low=close - 0.02,
        close=close, volume=1000, amount=1284,
        source="Tushare Pro", fetched_at="2026-08-08T00:00:00Z",
    )

def test_normalize_code_understands_shanghai_etf_and_stock():
    assert normalize_code("512480") == "512480.SH"
    assert normalize_code("600519.SH") == "600519.SH"

def test_cache_upserts_and_returns_sorted_bars(tmp_path):
    cache = MarketCache(tmp_path / "test.db")
    cache.upsert_bars("Tushare Pro", [bar(3, 1.30), bar(2, 1.28), bar(3, 1.31)])
    rows = cache.get_bars("Tushare Pro", "512480.SH", date(2026, 1, 1), date(2026, 1, 3))
    assert [(row.trade_date.day, row.close) for row in rows] == [(2, 1.28), (3, 1.31)]


def test_cache_omits_legacy_rows_that_fail_price_bar_validation(tmp_path):
    cache = MarketCache(tmp_path / "test.db")
    cache.upsert_bars("Tushare Pro", [bar(2, 1.28)])
    with sqlite3.connect(cache.db_path) as conn:
        conn.execute("""
            INSERT INTO price_bars (
                dataset, code, trade_date, open, high, low, close,
                volume, amount, source, fetched_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            "Tushare Pro", "512480.SH", "2026-01-03", 1.2, 1.3, 1.1,
            1.2, -1, 1000, "Tushare Pro", "2026-08-08T00:00:00Z",
        ))

    rows = cache.get_bars(
        "Tushare Pro", "512480.SH", date(2026, 1, 1), date(2026, 1, 3)
    )

    assert [(row.trade_date.day, row.close) for row in rows] == [(2, 1.28)]

def test_cache_creates_missing_parent_directory(tmp_path):
    db_path = tmp_path / "nested" / "cache" / "test.db"
    MarketCache(db_path)
    assert db_path.is_file()

def test_missing_ranges_subtracts_synced_intervals(tmp_path):
    cache = MarketCache(tmp_path / "test.db")
    cache.mark_synced("Tushare Pro", "512480.SH", date(2026, 1, 3), date(2026, 1, 7))
    assert cache.missing_ranges("Tushare Pro", "512480.SH", date(2026, 1, 1), date(2026, 1, 10)) == [
        (date(2026, 1, 1), date(2026, 1, 2)),
        (date(2026, 1, 8), date(2026, 1, 10)),
    ]


def test_cache_reports_covered_days_and_provider_cooldown(tmp_path):
    cache = MarketCache(tmp_path / "test.db")
    cache.mark_synced("Tushare Pro", "512480.SH", date(2026, 1, 3), date(2026, 1, 7))
    cache.mark_synced("Tushare Pro", "512480.SH", date(2026, 1, 8), date(2026, 1, 9))

    assert cache.coverage_days("Tushare Pro", "512480.SH", date(2026, 1, 1), date(2026, 1, 10)) == 7
    assert cache.provider_in_cooldown("512480.SH", "Tushare Pro") is False

    cooldown_until = cache.record_provider_failure("512480.SH", "Tushare Pro")
    assert cooldown_until > datetime.now(timezone.utc)
    assert cache.provider_in_cooldown("512480.SH", "Tushare Pro") is True

    cache.record_provider_success("512480.SH", "Tushare Pro")
    assert cache.provider_in_cooldown("512480.SH", "Tushare Pro") is False
    assert cache.get_preferred_provider("512480.SH") == "Tushare Pro"


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
                1000, 1000, 'Tushare Pro', '2026-08-08T00:00:00Z'
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

    assert len(cache.get_bars("Tushare Pro", "512480.SH", date(2026, 1, 1), date(2026, 1, 31))) == 1
    assert cache.missing_ranges(
        "Tushare Pro", "512480.SH", date(2026, 1, 1), date(2026, 1, 31)
    ) == [(date(2026, 1, 1), date(2026, 1, 31))]


def test_calendar_v2_migration_preserves_disjoint_bars_without_range_coverage(tmp_path):
    db_path = tmp_path / "v1.db"
    with sqlite3.connect(db_path) as conn:
        conn.execute("""
            CREATE TABLE price_bars (
                dataset TEXT NOT NULL, code TEXT NOT NULL, trade_date TEXT NOT NULL,
                open REAL NOT NULL, high REAL NOT NULL, low REAL NOT NULL,
                close REAL NOT NULL, volume REAL NOT NULL, amount REAL,
                source TEXT NOT NULL, fetched_at TEXT NOT NULL,
                PRIMARY KEY (dataset, code, trade_date)
            )
        """)
        for day in ("2026-01-02", "2026-01-05"):
            conn.execute("""
                INSERT INTO price_bars VALUES (
                    'Tushare Pro', '512480.SH', ?, 1.0, 1.1, 0.9, 1.0,
                    1000, 1000, 'Tushare Pro', '2026-08-08T00:00:00Z'
                )
            """, (day,))
        conn.execute("""
            CREATE TABLE sync_ranges (
                dataset TEXT NOT NULL, code TEXT NOT NULL,
                start_date TEXT NOT NULL, end_date TEXT NOT NULL,
                PRIMARY KEY (dataset, code, start_date, end_date)
            )
        """)
        conn.execute("""
            INSERT INTO sync_ranges VALUES (
                'Tushare Pro', '512480.SH', '2026-01-02', '2026-01-05'
            )
        """)
        conn.execute("CREATE TABLE cache_metadata (key TEXT PRIMARY KEY, value TEXT NOT NULL)")
        conn.execute("INSERT INTO cache_metadata VALUES ('sync_policy_version', 'tushare-observed-boundaries-v1')")

    cache = MarketCache(db_path)

    assert len(cache.get_bars(
        "Tushare Pro", "512480.SH", date(2026, 1, 1), date(2026, 1, 31)
    )) == 2
    assert cache.missing_ranges(
        "Tushare Pro", "512480.SH", date(2026, 1, 2), date(2026, 1, 5)
    ) == [(date(2026, 1, 2), date(2026, 1, 5))]


def test_catalog_snapshot_and_asset_profile_round_trip_through_sqlite(tmp_path):
    cache = MarketCache(tmp_path / "market.db")
    fetched_at = datetime(2026, 8, 29, tzinfo=timezone.utc)
    instrument = Instrument(
        code="512480.SH",
        name="半导体 ETF",
        asset_type="etf",
        exchange="SH",
    )
    metadata = {
        "index_name": "中证全指半导体产品与设备指数",
        "list_date": "20190612",
    }
    cache.replace_instrument_catalog(
        "Tushare Pro", [(instrument, metadata)], fetched_at
    )

    catalog, stored_at = cache.get_instrument_catalog("Tushare Pro")
    assert catalog == [(instrument, metadata)]
    assert stored_at == fetched_at

    profile = AssetProfile(
        code="512480.SH",
        asset_type="etf",
        etf=EtfProfile(
            tracking_index=metadata["index_name"],
            availability=Availability(status="available"),
        ),
    )
    cache.upsert_asset_profile("Tushare Pro", profile, fetched_at)

    assert cache.get_asset_profile("Tushare Pro", "512480.SH") == (
        profile,
        fetched_at,
    )


def test_replacing_catalog_removes_rows_missing_from_new_snapshot(tmp_path):
    cache = MarketCache(tmp_path / "market.db")
    first = Instrument(
        code="512480.SH", name="半导体 ETF", asset_type="etf", exchange="SH"
    )
    second = Instrument(
        code="600519.SH", name="贵州茅台", asset_type="equity", exchange="SH"
    )
    cache.replace_instrument_catalog(
        "Tushare Pro", [(first, {}), (second, {})]
    )
    cache.replace_instrument_catalog("Tushare Pro", [(second, {})])

    catalog, _ = cache.get_instrument_catalog("Tushare Pro")
    assert [instrument.code for instrument, _ in catalog] == ["600519.SH"]
