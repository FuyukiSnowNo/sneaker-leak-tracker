# database/db.py
import sqlite3
import logging
from datetime import datetime, timezone
from typing import Optional
from contextlib import contextmanager

import config
from scrapers.base import LeakItem

logger = logging.getLogger(__name__)

SCHEMA = """
CREATE TABLE IF NOT EXISTS leaks (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    title        TEXT    NOT NULL,
    url          TEXT    UNIQUE NOT NULL,
    source       TEXT    NOT NULL,
    source_name  TEXT    NOT NULL,
    summary      TEXT    DEFAULT '',
    brand        TEXT    DEFAULT 'Other',
    hype_score   INTEGER DEFAULT 0,
    hype_tier    TEXT    DEFAULT 'LOW',
    release_date TEXT    DEFAULT 'TBD',
    tags         TEXT    DEFAULT '',
    image_url    TEXT    DEFAULT '',
    image_path   TEXT    DEFAULT '',
    published_at TEXT,
    scraped_at   TEXT    NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_brand      ON leaks(brand);
CREATE INDEX IF NOT EXISTS idx_hype_tier  ON leaks(hype_tier);
CREATE INDEX IF NOT EXISTS idx_source     ON leaks(source);
CREATE INDEX IF NOT EXISTS idx_scraped_at ON leaks(scraped_at);
CREATE INDEX IF NOT EXISTS idx_published  ON leaks(published_at);
"""


class Database:
    def __init__(self, path: str = config.DATABASE_PATH):
        self.path = path
        self._init_db()

    @contextmanager
    def _conn(self):
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def _init_db(self):
        with self._conn() as conn:
            conn.executescript(SCHEMA)
            # Migrate existing DB: add columns if missing
            existing = {r[1] for r in conn.execute("PRAGMA table_info(leaks)").fetchall()}
            for col, definition in [
                ("image_url",  "TEXT DEFAULT ''"),
                ("image_path", "TEXT DEFAULT ''"),
            ]:
                if col not in existing:
                    conn.execute(f"ALTER TABLE leaks ADD COLUMN {col} {definition}")
                    logger.info(f"Migrated DB: added column '{col}'")

    def insert_many(self, items: list[LeakItem]) -> tuple[int, int]:
        inserted = skipped = 0
        with self._conn() as conn:
            for item in items:
                d = item.to_dict()
                try:
                    conn.execute("""
                        INSERT INTO leaks
                            (title, url, source, source_name, summary, brand,
                             hype_score, hype_tier, release_date, tags,
                             image_url, image_path, published_at, scraped_at)
                        VALUES
                            (:title, :url, :source, :source_name, :summary, :brand,
                             :hype_score, :hype_tier, :release_date, :tags,
                             :image_url, :image_path, :published_at, :scraped_at)
                    """, d)
                    inserted += 1
                except sqlite3.IntegrityError:
                    skipped += 1
        return inserted, skipped

    def update_image_path(self, url: str, image_path: str):
        """Called after downloading — writes local path back to DB row."""
        with self._conn() as conn:
            conn.execute(
                "UPDATE leaks SET image_path = ? WHERE url = ?",
                (image_path, url)
            )

    def query(self, since=None, until=None, brand=None, source=None,
              min_hype=None, hype_tier=None, limit=1000) -> list[dict]:
        clauses, params = [], []
        if since:
            clauses.append("scraped_at >= ?"); params.append(since.isoformat())
        if until:
            clauses.append("scraped_at <= ?"); params.append(until.isoformat())
        if brand:
            clauses.append("brand = ?"); params.append(brand)
        if source:
            clauses.append("source = ?"); params.append(source)
        if min_hype is not None:
            clauses.append("hype_score >= ?"); params.append(min_hype)
        if hype_tier:
            clauses.append("hype_tier = ?"); params.append(hype_tier)
        where = ("WHERE " + " AND ".join(clauses)) if clauses else ""
        sql   = f"SELECT * FROM leaks {where} ORDER BY scraped_at DESC LIMIT ?"
        params.append(limit)
        with self._conn() as conn:
            return [dict(r) for r in conn.execute(sql, params).fetchall()]

    def count(self) -> int:
        with self._conn() as conn:
            return conn.execute("SELECT COUNT(*) FROM leaks").fetchone()[0]

    def brand_counts(self, since=None, until=None) -> list[dict]:
        clauses, params = self._date_clauses(since, until)
        where = ("WHERE " + " AND ".join(clauses)) if clauses else ""
        with self._conn() as conn:
            return [dict(r) for r in conn.execute(
                f"SELECT brand, COUNT(*) as count FROM leaks {where} GROUP BY brand ORDER BY count DESC",
                params).fetchall()]

    def source_counts(self, since=None, until=None) -> list[dict]:
        clauses, params = self._date_clauses(since, until)
        where = ("WHERE " + " AND ".join(clauses)) if clauses else ""
        with self._conn() as conn:
            return [dict(r) for r in conn.execute(
                f"SELECT source_name, COUNT(*) as count FROM leaks {where} GROUP BY source_name ORDER BY count DESC",
                params).fetchall()]

    def hype_distribution(self, since=None, until=None) -> list[dict]:
        clauses, params = self._date_clauses(since, until)
        where = ("WHERE " + " AND ".join(clauses)) if clauses else ""
        with self._conn() as conn:
            return [dict(r) for r in conn.execute(
                f"SELECT hype_tier, COUNT(*) as count FROM leaks {where} GROUP BY hype_tier ORDER BY count DESC",
                params).fetchall()]

    def daily_counts(self, since=None, until=None) -> list[dict]:
        clauses, params = self._date_clauses(since, until)
        where = ("WHERE " + " AND ".join(clauses)) if clauses else ""
        with self._conn() as conn:
            return [dict(r) for r in conn.execute(
                f"SELECT DATE(scraped_at) as day, COUNT(*) as count FROM leaks {where} GROUP BY day ORDER BY day",
                params).fetchall()]

    def top_hype(self, since=None, until=None, n=10) -> list[dict]:
        clauses, params = self._date_clauses(since, until)
        where = ("WHERE " + " AND ".join(clauses)) if clauses else ""
        params.append(n)
        with self._conn() as conn:
            return [dict(r) for r in conn.execute(
                f"SELECT title, source_name, hype_score, hype_tier, brand, release_date, url, image_url, image_path "
                f"FROM leaks {where} ORDER BY hype_score DESC LIMIT ?",
                params).fetchall()]

    @staticmethod
    def _date_clauses(since, until):
        clauses, params = [], []
        if since:
            clauses.append("scraped_at >= ?"); params.append(since.isoformat())
        if until:
            clauses.append("scraped_at <= ?"); params.append(until.isoformat())
        return clauses, params
