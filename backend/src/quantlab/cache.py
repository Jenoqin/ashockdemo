import json
import sqlite3
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import List, Mapping, Tuple

from pydantic import ValidationError

from quantlab.models import AssetProfile, Instrument, PriceBar


SYNC_POLICY_VERSION = "tushare-calendar-v2"


class MarketCache:
    def __init__(self, db_path: str):
        self.db_path = str(db_path)
        if self.db_path != ":memory:":
            Path(self.db_path).expanduser().parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            self._migrate_legacy_schema(conn)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS price_bars (
                    dataset TEXT NOT NULL,
                    code TEXT NOT NULL,
                    trade_date TEXT NOT NULL,
                    open REAL NOT NULL,
                    high REAL NOT NULL,
                    low REAL NOT NULL,
                    close REAL NOT NULL,
                    volume REAL NOT NULL,
                    amount REAL,
                    source TEXT NOT NULL,
                    fetched_at TEXT NOT NULL,
                    PRIMARY KEY (dataset, code, trade_date)
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS sync_ranges (
                    dataset TEXT NOT NULL,
                    code TEXT NOT NULL,
                    start_date TEXT NOT NULL,
                    end_date TEXT NOT NULL,
                    PRIMARY KEY (dataset, code, start_date, end_date)
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS market_calendar (
                    exchange TEXT NOT NULL,
                    cal_date TEXT NOT NULL,
                    is_open INTEGER NOT NULL CHECK (is_open IN (0, 1)),
                    fetched_at TEXT NOT NULL,
                    PRIMARY KEY (exchange, cal_date)
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS no_bar_dates (
                    dataset TEXT NOT NULL,
                    code TEXT NOT NULL,
                    trade_date TEXT NOT NULL,
                    reason TEXT NOT NULL,
                    confirmed_at TEXT NOT NULL,
                    PRIMARY KEY (dataset, code, trade_date)
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS provider_state (
                    code TEXT NOT NULL,
                    data_kind TEXT NOT NULL,
                    adjustment TEXT NOT NULL,
                    provider TEXT NOT NULL,
                    last_success_at TEXT,
                    last_failure_at TEXT,
                    consecutive_failures INTEGER NOT NULL DEFAULT 0,
                    cooldown_until TEXT,
                    PRIMARY KEY (code, data_kind, adjustment, provider)
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS cache_metadata (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS instrument_catalog (
                    provider TEXT NOT NULL,
                    code TEXT NOT NULL,
                    name TEXT NOT NULL,
                    full_name TEXT,
                    asset_type TEXT NOT NULL
                        CHECK (asset_type IN ('etf', 'equity')),
                    exchange TEXT NOT NULL
                        CHECK (exchange IN ('SH', 'SZ', 'BJ')),
                    metadata_json TEXT NOT NULL,
                    fetched_at TEXT NOT NULL,
                    PRIMARY KEY (provider, code)
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS asset_profiles (
                    provider TEXT NOT NULL,
                    code TEXT NOT NULL,
                    profile_json TEXT NOT NULL,
                    fetched_at TEXT NOT NULL,
                    PRIMARY KEY (provider, code)
                )
            """)
            self._migrate_sync_policy(conn)

    def replace_instrument_catalog(
        self,
        provider: str,
        entries: list[tuple[Instrument, dict]],
        fetched_at: datetime | None = None,
    ) -> datetime:
        """Atomically replace one provider's complete security catalog."""
        if not entries:
            raise ValueError("instrument catalog must not be empty")
        fetched_at = fetched_at or datetime.now(timezone.utc)
        fetched_at_text = fetched_at.isoformat()
        rows = [
            (
                provider,
                instrument.code,
                instrument.name,
                instrument.full_name,
                instrument.asset_type,
                instrument.exchange,
                json.dumps(metadata, ensure_ascii=False, allow_nan=False),
                fetched_at_text,
            )
            for instrument, metadata in entries
        ]
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "DELETE FROM instrument_catalog WHERE provider = ?",
                (provider,),
            )
            conn.executemany("""
                INSERT INTO instrument_catalog (
                    provider, code, name, full_name, asset_type, exchange,
                    metadata_json, fetched_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, rows)
        return fetched_at

    def get_instrument_catalog(
        self, provider: str
    ) -> tuple[list[tuple[Instrument, dict]], datetime] | None:
        """Load a provider catalog only when the stored snapshot is coherent."""
        with sqlite3.connect(self.db_path) as conn:
            rows = conn.execute("""
                SELECT code, name, full_name, asset_type, exchange,
                       metadata_json, fetched_at
                FROM instrument_catalog
                WHERE provider = ?
                ORDER BY code
            """, (provider,)).fetchall()
        if not rows:
            return None
        fetched_values = {row[6] for row in rows}
        if len(fetched_values) != 1:
            return None
        try:
            fetched_at = datetime.fromisoformat(rows[0][6])
            entries = [
                (
                    Instrument(
                        code=row[0],
                        name=row[1],
                        full_name=row[2],
                        asset_type=row[3],
                        exchange=row[4],
                    ),
                    json.loads(row[5]),
                )
                for row in rows
            ]
        except (TypeError, ValueError, json.JSONDecodeError):
            return None
        if any(not isinstance(metadata, dict) for _, metadata in entries):
            return None
        return entries, fetched_at

    def upsert_asset_profile(
        self,
        provider: str,
        profile: AssetProfile,
        fetched_at: datetime | None = None,
    ) -> datetime:
        fetched_at = fetched_at or datetime.now(timezone.utc)
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO asset_profiles (
                    provider, code, profile_json, fetched_at
                ) VALUES (?, ?, ?, ?)
                ON CONFLICT(provider, code) DO UPDATE SET
                    profile_json = excluded.profile_json,
                    fetched_at = excluded.fetched_at
            """, (
                provider,
                profile.code,
                profile.model_dump_json(),
                fetched_at.isoformat(),
            ))
        return fetched_at

    def get_asset_profile(
        self, provider: str, code: str
    ) -> tuple[AssetProfile, datetime] | None:
        with sqlite3.connect(self.db_path) as conn:
            row = conn.execute("""
                SELECT profile_json, fetched_at
                FROM asset_profiles
                WHERE provider = ? AND code = ?
            """, (provider, code)).fetchone()
        if not row:
            return None
        try:
            return AssetProfile.model_validate_json(row[0]), datetime.fromisoformat(row[1])
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _table_columns(conn: sqlite3.Connection, table: str) -> set[str]:
        return {row[1] for row in conn.execute(f"PRAGMA table_info({table})")}

    def _migrate_legacy_schema(self, conn: sqlite3.Connection) -> None:
        """Separate legacy rows by recorded source and invalidate unsafe sync state."""
        price_columns = self._table_columns(conn, "price_bars")
        if price_columns and "dataset" not in price_columns:
            conn.execute("ALTER TABLE price_bars RENAME TO price_bars_legacy")
            conn.execute("""
                CREATE TABLE price_bars (
                    dataset TEXT NOT NULL,
                    code TEXT NOT NULL,
                    trade_date TEXT NOT NULL,
                    open REAL NOT NULL,
                    high REAL NOT NULL,
                    low REAL NOT NULL,
                    close REAL NOT NULL,
                    volume REAL NOT NULL,
                    amount REAL,
                    source TEXT NOT NULL,
                    fetched_at TEXT NOT NULL,
                    PRIMARY KEY (dataset, code, trade_date)
                )
            """)
            conn.execute("""
                INSERT INTO price_bars (
                    dataset, code, trade_date, open, high, low, close,
                    volume, amount, source, fetched_at
                )
                SELECT COALESCE(NULLIF(source, ''), 'legacy'), code, trade_date,
                       open, high, low, close, volume, amount,
                       COALESCE(NULLIF(source, ''), 'legacy'), fetched_at
                FROM price_bars_legacy
            """)
            conn.execute("DROP TABLE price_bars_legacy")

        sync_columns = self._table_columns(conn, "sync_ranges")
        if sync_columns and "dataset" not in sync_columns:
            # The old ranges did not record a provider, so they cannot safely
            # authorize cache reuse after switching data source or app mode.
            conn.execute("DROP TABLE sync_ranges")

    @staticmethod
    def _migrate_sync_policy(conn: sqlite3.Connection) -> None:
        """Invalidate range-based Tushare coverage without deleting cached bars."""
        row = conn.execute(
            "SELECT value FROM cache_metadata WHERE key = 'sync_policy_version'"
        ).fetchone()
        if row and row[0] == SYNC_POLICY_VERSION:
            return

        # MIN/MAX coverage cannot prove that every internal trading date was
        # observed. Keep the legacy table for compatibility with other data
        # sets, but never carry Tushare ranges into the calendar-v2 policy.
        conn.execute("DELETE FROM sync_ranges WHERE dataset = ?", ("Tushare Pro",))
        conn.execute("""
            INSERT INTO cache_metadata (key, value)
            VALUES ('sync_policy_version', ?)
            ON CONFLICT(key) DO UPDATE SET value = excluded.value
        """, (SYNC_POLICY_VERSION,))

    def get_calendar(
        self, exchange: str, start: date, end: date
    ) -> dict[date, bool]:
        with sqlite3.connect(self.db_path) as conn:
            rows = conn.execute("""
                SELECT cal_date, is_open FROM market_calendar
                WHERE exchange = ? AND cal_date >= ? AND cal_date <= ?
                ORDER BY cal_date ASC
            """, (exchange, start.isoformat(), end.isoformat())).fetchall()
        return {date.fromisoformat(day): bool(is_open) for day, is_open in rows}

    def get_no_bar_dates(
        self, dataset: str, code: str, start: date, end: date
    ) -> dict[date, str]:
        with sqlite3.connect(self.db_path) as conn:
            rows = conn.execute("""
                SELECT trade_date, reason FROM no_bar_dates
                WHERE dataset = ? AND code = ?
                  AND trade_date >= ? AND trade_date <= ?
                ORDER BY trade_date ASC
            """, (dataset, code, start.isoformat(), end.isoformat())).fetchall()
        return {date.fromisoformat(day): reason for day, reason in rows}

    def commit_verified(
        self,
        dataset: str,
        code: str,
        calendars: Mapping[str, Mapping[date, bool]],
        bars: List[PriceBar],
        no_bars: Mapping[date, str],
    ) -> None:
        """Atomically commit only a fully verified provider result."""
        now = datetime.now(timezone.utc).isoformat()
        with sqlite3.connect(self.db_path) as conn:
            calendar_rows = [
                (exchange, cal_date.isoformat(), int(is_open), now)
                for exchange, values in calendars.items()
                for cal_date, is_open in values.items()
            ]
            if calendar_rows:
                conn.executemany("""
                    INSERT INTO market_calendar (
                        exchange, cal_date, is_open, fetched_at
                    ) VALUES (?, ?, ?, ?)
                    ON CONFLICT(exchange, cal_date) DO UPDATE SET
                        is_open = excluded.is_open,
                        fetched_at = excluded.fetched_at
                """, calendar_rows)

            if bars:
                conn.executemany("""
                    INSERT INTO price_bars (
                        dataset, code, trade_date, open, high, low, close,
                        volume, amount, source, fetched_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(dataset, code, trade_date) DO UPDATE SET
                        open=excluded.open,
                        high=excluded.high,
                        low=excluded.low,
                        close=excluded.close,
                        volume=excluded.volume,
                        amount=excluded.amount,
                        source=excluded.source,
                        fetched_at=excluded.fetched_at
                """, [
                    (
                        dataset, bar.code, bar.trade_date.isoformat(), bar.open,
                        bar.high, bar.low, bar.close, bar.volume, bar.amount,
                        bar.source, bar.fetched_at.isoformat(),
                    )
                    for bar in bars
                ])
                conn.executemany("""
                    DELETE FROM no_bar_dates
                    WHERE dataset = ? AND code = ? AND trade_date = ?
                """, [
                    (dataset, code, bar.trade_date.isoformat()) for bar in bars
                ])

            if no_bars:
                no_bar_rows = [
                    (dataset, code, trade_date.isoformat(), reason, now)
                    for trade_date, reason in no_bars.items()
                ]
                conn.executemany("""
                    DELETE FROM price_bars
                    WHERE dataset = ? AND code = ? AND trade_date = ?
                """, [row[:3] for row in no_bar_rows])
                conn.executemany("""
                    INSERT INTO no_bar_dates (
                        dataset, code, trade_date, reason, confirmed_at
                    ) VALUES (?, ?, ?, ?, ?)
                    ON CONFLICT(dataset, code, trade_date) DO UPDATE SET
                        reason = excluded.reason,
                        confirmed_at = excluded.confirmed_at
                """, no_bar_rows)

    def upsert_bars(self, dataset: str, bars: List[PriceBar]):
        if not bars:
            return
        with sqlite3.connect(self.db_path) as conn:
            conn.executemany("""
                INSERT INTO price_bars (
                    dataset, code, trade_date, open, high, low, close,
                    volume, amount, source, fetched_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(dataset, code, trade_date) DO UPDATE SET
                    open=excluded.open,
                    high=excluded.high,
                    low=excluded.low,
                    close=excluded.close,
                    volume=excluded.volume,
                    amount=excluded.amount,
                    source=excluded.source,
                    fetched_at=excluded.fetched_at
            """, [
                (
                    dataset, b.code, b.trade_date.isoformat(), b.open, b.high,
                    b.low, b.close, b.volume, b.amount, b.source,
                    b.fetched_at.isoformat(),
                )
                for b in bars
            ])

    def replace_range(
        self,
        dataset: str,
        code: str,
        start: date,
        end: date,
        bars: List[PriceBar],
    ) -> None:
        """Atomically replace one provider's range, including stale holiday rows."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                DELETE FROM price_bars
                WHERE dataset = ? AND code = ?
                  AND trade_date >= ? AND trade_date <= ?
            """, (dataset, code, start.isoformat(), end.isoformat()))
            conn.executemany("""
                INSERT INTO price_bars (
                    dataset, code, trade_date, open, high, low, close,
                    volume, amount, source, fetched_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, [
                (
                    dataset, b.code, b.trade_date.isoformat(), b.open, b.high,
                    b.low, b.close, b.volume, b.amount, b.source,
                    b.fetched_at.isoformat(),
                )
                for b in bars
            ])
            self._mark_synced(conn, dataset, code, start, end)

    def get_bars(
        self, dataset: str, code: str, start: date, end: date
    ) -> List[PriceBar]:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("""
                SELECT code, trade_date, open, high, low, close,
                       volume, amount, source, fetched_at
                FROM price_bars
                WHERE dataset = ? AND code = ?
                  AND trade_date >= ? AND trade_date <= ?
                ORDER BY trade_date ASC
            """, (dataset, code, start.isoformat(), end.isoformat()))
            bars: list[PriceBar] = []
            for row in cursor:
                try:
                    bars.append(PriceBar.model_validate(dict(row)))
                except ValidationError:
                    # Legacy/corrupted cache rows are never allowed back across
                    # the model boundary. Omitting the row makes its date an
                    # ordinary cache miss so a valid provider result can repair it.
                    continue
            return bars

    def mark_synced(
        self, dataset: str, code: str, start: date, end: date
    ) -> None:
        with sqlite3.connect(self.db_path) as conn:
            self._mark_synced(conn, dataset, code, start, end)

    @staticmethod
    def _mark_synced(
        conn: sqlite3.Connection,
        dataset: str,
        code: str,
        start: date,
        end: date,
    ) -> None:
        cursor = conn.execute("""
            SELECT start_date, end_date FROM sync_ranges
            WHERE dataset = ? AND code = ?
              AND start_date <= ? AND end_date >= ?
        """, (dataset, code, end.isoformat(), start.isoformat()))
        new_start = start.isoformat()
        new_end = end.isoformat()
        for range_start, range_end in cursor.fetchall():
            new_start = min(new_start, range_start)
            new_end = max(new_end, range_end)
        conn.execute("""
            DELETE FROM sync_ranges
            WHERE dataset = ? AND code = ?
              AND start_date <= ? AND end_date >= ?
        """, (dataset, code, end.isoformat(), start.isoformat()))
        conn.execute("""
            INSERT INTO sync_ranges (dataset, code, start_date, end_date)
            VALUES (?, ?, ?, ?)
        """, (dataset, code, new_start, new_end))

    def missing_ranges(
        self, dataset: str, code: str, start: date, end: date
    ) -> List[Tuple[date, date]]:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT start_date, end_date FROM sync_ranges
                WHERE dataset = ? AND code = ?
                  AND end_date >= ? AND start_date <= ?
                ORDER BY start_date ASC
            """, (dataset, code, start.isoformat(), end.isoformat()))
            synced = cursor.fetchall()

        missing = []
        current_start = start
        for range_start, range_end in synced:
            synced_start = date.fromisoformat(range_start)
            synced_end = date.fromisoformat(range_end)
            if synced_start > current_start:
                gap_end = min(synced_start - timedelta(days=1), end)
                if current_start <= gap_end:
                    missing.append((current_start, gap_end))
            if synced_end >= current_start:
                current_start = max(current_start, synced_end + timedelta(days=1))

        if current_start <= end:
            missing.append((current_start, end))
        return missing

    def coverage_days(
        self, dataset: str, code: str, start: date, end: date
    ) -> int:
        """Return the number of requested calendar days covered by sync ranges."""
        with sqlite3.connect(self.db_path) as conn:
            rows = conn.execute("""
                SELECT start_date, end_date FROM sync_ranges
                WHERE dataset = ? AND code = ?
                  AND end_date >= ? AND start_date <= ?
                ORDER BY start_date ASC
            """, (dataset, code, start.isoformat(), end.isoformat())).fetchall()

        intervals = [
            (max(start, date.fromisoformat(range_start)), min(end, date.fromisoformat(range_end)))
            for range_start, range_end in rows
        ]
        if not intervals:
            return 0

        covered = 0
        current_start, current_end = intervals[0]
        for interval_start, interval_end in intervals[1:]:
            if interval_start <= current_end + timedelta(days=1):
                current_end = max(current_end, interval_end)
            else:
                covered += (current_end - current_start).days + 1
                current_start, current_end = interval_start, interval_end
        return covered + (current_end - current_start).days + 1

    def get_preferred_provider(
        self,
        code: str,
        data_kind: str = "daily",
        adjustment: str = "hfq",
    ) -> str | None:
        with sqlite3.connect(self.db_path) as conn:
            row = conn.execute("""
                SELECT provider FROM provider_state
                WHERE code = ? AND data_kind = ? AND adjustment = ?
                  AND last_success_at IS NOT NULL
                ORDER BY last_success_at DESC
                LIMIT 1
            """, (code, data_kind, adjustment)).fetchone()
        return row[0] if row else None

    def record_provider_success(
        self,
        code: str,
        provider: str,
        data_kind: str = "daily",
        adjustment: str = "hfq",
    ) -> None:
        now = datetime.now(timezone.utc).isoformat()
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO provider_state (
                    code, data_kind, adjustment, provider, last_success_at,
                    last_failure_at, consecutive_failures, cooldown_until
                ) VALUES (?, ?, ?, ?, ?, NULL, 0, NULL)
                ON CONFLICT(code, data_kind, adjustment, provider) DO UPDATE SET
                    last_success_at = excluded.last_success_at,
                    consecutive_failures = 0,
                    cooldown_until = NULL
            """, (code, data_kind, adjustment, provider, now))

    def record_provider_failure(
        self,
        code: str,
        provider: str,
        data_kind: str = "daily",
        adjustment: str = "hfq",
    ) -> datetime:
        now = datetime.now(timezone.utc)
        with sqlite3.connect(self.db_path) as conn:
            row = conn.execute("""
                SELECT consecutive_failures FROM provider_state
                WHERE code = ? AND data_kind = ? AND adjustment = ?
                  AND provider = ?
            """, (code, data_kind, adjustment, provider)).fetchone()
            failures = (row[0] if row else 0) + 1
            cooldown_minutes = 5 if failures == 1 else 30 if failures == 2 else 120
            cooldown_until = now + timedelta(minutes=cooldown_minutes)
            conn.execute("""
                INSERT INTO provider_state (
                    code, data_kind, adjustment, provider, last_success_at,
                    last_failure_at, consecutive_failures, cooldown_until
                ) VALUES (?, ?, ?, ?, NULL, ?, ?, ?)
                ON CONFLICT(code, data_kind, adjustment, provider) DO UPDATE SET
                    last_failure_at = excluded.last_failure_at,
                    consecutive_failures = excluded.consecutive_failures,
                    cooldown_until = excluded.cooldown_until
            """, (
                code,
                data_kind,
                adjustment,
                provider,
                now.isoformat(),
                failures,
                cooldown_until.isoformat(),
            ))
        return cooldown_until

    def provider_in_cooldown(
        self,
        code: str,
        provider: str,
        data_kind: str = "daily",
        adjustment: str = "hfq",
    ) -> bool:
        with sqlite3.connect(self.db_path) as conn:
            row = conn.execute("""
                SELECT cooldown_until FROM provider_state
                WHERE code = ? AND data_kind = ? AND adjustment = ?
                  AND provider = ?
            """, (code, data_kind, adjustment, provider)).fetchone()
        if not row or not row[0]:
            return False
        return datetime.fromisoformat(row[0]) > datetime.now(timezone.utc)
