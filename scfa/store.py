"""PostgreSQL storage (SQLite for tests and local runs).

Raw requests are kept for RAW_RETENTION_DAYS; per-minute rollups are kept for
the life of the program. No IPs, user agents or query strings are stored, which
keeps the API side as privacy-first as the Umami web side.
"""
from __future__ import annotations

import hashlib
import os
import secrets
import sqlite3
import time
from contextlib import contextmanager

from .otlp import ApiRequest

RAW_RETENTION_DAYS = 30

SCHEMA = [
    """CREATE TABLE IF NOT EXISTS projects (
        id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        key_hash TEXT NOT NULL UNIQUE,
        umami_website_id TEXT,
        created_at BIGINT NOT NULL)""",
    """CREATE TABLE IF NOT EXISTS api_requests (
        project_id TEXT NOT NULL,
        service TEXT NOT NULL,
        route TEXT NOT NULL,
        method TEXT NOT NULL,
        status INTEGER NOT NULL,
        duration_ms DOUBLE PRECISION NOT NULL,
        ts BIGINT NOT NULL)""",
    "CREATE INDEX IF NOT EXISTS ix_req_project_ts ON api_requests (project_id, ts)",
    """CREATE TABLE IF NOT EXISTS alert_rules (
        project_id TEXT NOT NULL,
        metric TEXT NOT NULL,
        threshold DOUBLE PRECISION NOT NULL,
        window_min INTEGER NOT NULL,
        webhook_url TEXT,
        PRIMARY KEY (project_id, metric))""",
]


def hash_key(raw: str) -> str:
    return hashlib.sha256(raw.encode()).hexdigest()


class Store:
    """Thin DB-API wrapper. `dsn` is a postgres URL or a SQLite path."""

    def __init__(self, dsn: str | None = None):
        dsn = dsn or os.environ.get("DATABASE_URL", ":memory:")
        if dsn.startswith("postgres"):
            import psycopg  # optional dependency, only needed in production

            self.conn = psycopg.connect(dsn, autocommit=True)
            self.ph = "%s"
        else:
            self.conn = sqlite3.connect(dsn)
            self.ph = "?"
        for stmt in SCHEMA:
            self._exec(stmt)

    def _sql(self, sql: str) -> str:
        return sql.replace("?", self.ph)

    def _exec(self, sql, params=()):
        cur = self.conn.cursor()
        cur.execute(self._sql(sql), params)
        return cur

    @contextmanager
    def tx(self):
        try:
            yield
            self.conn.commit()
        except Exception:
            self.conn.rollback()
            raise

    # projects ------------------------------------------------------------
    def create_project(self, project_id: str, name: str, umami_website_id=None) -> str:
        """Create a tenant and return its ingest key (shown once, stored hashed)."""
        raw = "scfa_" + secrets.token_urlsafe(24)
        with self.tx():
            self._exec(
                "INSERT INTO projects (id, name, key_hash, umami_website_id, created_at) VALUES (?,?,?,?,?)",
                (project_id, name, hash_key(raw), umami_website_id, int(time.time())),
            )
        return raw

    def project_for_key(self, raw_key: str | None):
        if not raw_key:
            return None
        row = self._exec(
            "SELECT id, name FROM projects WHERE key_hash = ?", (hash_key(raw_key),)
        ).fetchone()
        return {"id": row[0], "name": row[1]} if row else None

    def projects(self):
        rows = self._exec("SELECT id, name, umami_website_id FROM projects ORDER BY id").fetchall()
        return [{"id": r[0], "name": r[1], "umami_website_id": r[2]} for r in rows]

    # requests ------------------------------------------------------------
    def insert_requests(self, project_id: str, reqs: list[ApiRequest]) -> int:
        with self.tx():
            cur = self.conn.cursor()
            cur.executemany(
                self._sql(
                    "INSERT INTO api_requests (project_id, service, route, method, status, duration_ms, ts) "
                    "VALUES (?,?,?,?,?,?,?)"
                ),
                [(project_id, r.service, r.route, r.method, r.status, r.duration_ms, r.ts_unix) for r in reqs],
            )
        return len(reqs)

    def requests_since(self, project_id: str | None, since_ts: int):
        sql = "SELECT project_id, route, method, status, duration_ms, ts FROM api_requests WHERE ts >= ?"
        params: tuple = (since_ts,)
        if project_id:
            sql += " AND project_id = ?"
            params += (project_id,)
        return self._exec(sql, params).fetchall()

    def purge_raw(self, now: int | None = None) -> int:
        cutoff = (now or int(time.time())) - RAW_RETENTION_DAYS * 86400
        with self.tx():
            cur = self._exec("DELETE FROM api_requests WHERE ts < ?", (cutoff,))
        return cur.rowcount

    # alert rules ---------------------------------------------------------
    def set_rule(self, project_id, metric, threshold, window_min=5, webhook_url=None):
        with self.tx():
            self._exec("DELETE FROM alert_rules WHERE project_id = ? AND metric = ?", (project_id, metric))
            self._exec(
                "INSERT INTO alert_rules (project_id, metric, threshold, window_min, webhook_url) VALUES (?,?,?,?,?)",
                (project_id, metric, threshold, window_min, webhook_url),
            )

    def rules(self):
        rows = self._exec(
            "SELECT project_id, metric, threshold, window_min, webhook_url FROM alert_rules"
        ).fetchall()
        return [dict(zip(("project_id", "metric", "threshold", "window_min", "webhook_url"), r)) for r in rows]
