import sqlite3
from datetime import date
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
            conn.execute("""
                CREATE TABLE IF NOT EXISTS price_bars (
                    code TEXT,
                    trade_date TEXT,
                    open REAL,
                    high REAL,
                    low REAL,
                    close REAL,
                    volume REAL,
                    amount REAL,
                    source TEXT,
                    fetched_at TEXT,
                    PRIMARY KEY (code, trade_date)
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS sync_ranges (
                    code TEXT,
                    start_date TEXT,
                    end_date TEXT,
                    PRIMARY KEY (code, start_date, end_date)
                )
            """)

    def upsert_bars(self, bars: List[PriceBar]):
        if not bars:
            return
        with sqlite3.connect(self.db_path) as conn:
            conn.executemany("""
                INSERT INTO price_bars (
                    code, trade_date, open, high, low, close, volume, amount, source, fetched_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(code, trade_date) DO UPDATE SET
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
                    b.code, b.trade_date.isoformat(), b.open, b.high, b.low, b.close,
                    b.volume, b.amount, b.source, b.fetched_at.isoformat()
                ) for b in bars
            ])

    def get_bars(self, code: str, start: date, end: date) -> List[PriceBar]:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("""
                SELECT * FROM price_bars
                WHERE code = ? AND trade_date >= ? AND trade_date <= ?
                ORDER BY trade_date ASC
            """, (code, start.isoformat(), end.isoformat()))
            return [PriceBar.model_validate(dict(row)) for row in cursor]

    def mark_synced(self, code: str, start: date, end: date):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT start_date, end_date FROM sync_ranges
                WHERE code = ? AND start_date <= ? AND end_date >= ?
            """, (code, end.isoformat(), start.isoformat()))
            
            new_start = start.isoformat()
            new_end = end.isoformat()
            
            rows = cursor.fetchall()
            for r_start, r_end in rows:
                new_start = min(new_start, r_start)
                new_end = max(new_end, r_end)
                
            conn.execute("""
                DELETE FROM sync_ranges
                WHERE code = ? AND start_date <= ? AND end_date >= ?
            """, (code, end.isoformat(), start.isoformat()))
            
            conn.execute("""
                INSERT INTO sync_ranges (code, start_date, end_date)
                VALUES (?, ?, ?)
            """, (code, new_start, new_end))

    def missing_ranges(self, code: str, start: date, end: date) -> List[Tuple[date, date]]:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT start_date, end_date FROM sync_ranges
                WHERE code = ? AND end_date >= ? AND start_date <= ?
                ORDER BY start_date ASC
            """, (code, start.isoformat(), end.isoformat()))
            
            synced = cursor.fetchall()
            
        missing = []
        current_start = start
        
        for r_start_str, r_end_str in synced:
            r_start = date.fromisoformat(r_start_str)
            r_end = date.fromisoformat(r_end_str)
            
            if r_start > current_start:
                # Missing gap before this synced range
                import datetime
                gap_end = min(r_start - datetime.timedelta(days=1), end)
                if current_start <= gap_end:
                    missing.append((current_start, gap_end))
            
            import datetime
            if r_end >= current_start:
                current_start = max(current_start, r_end + datetime.timedelta(days=1))
                
        if current_start <= end:
            missing.append((current_start, end))
            
        return missing
