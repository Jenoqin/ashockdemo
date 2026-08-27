import sqlite3
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import List, Tuple

from quantlab.models import PriceBar


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
            return [PriceBar.model_validate(dict(row)) for row in cursor]

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
