"""Read web-analytics totals from a self-hosted Umami instance.

Uses Umami's REST API: POST /api/auth/login, then
GET /api/websites/{id}/stats?startAt=<ms>&endAt=<ms>.
"""
from __future__ import annotations

import json
import urllib.request


class Umami:
    def __init__(self, base_url: str, username: str, password: str, timeout: float = 10):
        self.base = base_url.rstrip("/")
        self.timeout = timeout
        self.token = self._post("/api/auth/login", {"username": username, "password": password})["token"]

    def _post(self, path, body):
        req = urllib.request.Request(self.base + path, data=json.dumps(body).encode(),
                                     headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=self.timeout) as r:
            return json.load(r)

    def _get(self, path):
        req = urllib.request.Request(self.base + path, headers={"Authorization": f"Bearer {self.token}"})
        with urllib.request.urlopen(req, timeout=self.timeout) as r:
            return json.load(r)

    def stats(self, website_id: str, start_ms: int, end_ms: int) -> dict:
        raw = self._get(f"/api/websites/{website_id}/stats?startAt={start_ms}&endAt={end_ms}")
        return normalize_stats(raw)


def normalize_stats(raw: dict) -> dict:
    """Umami v2 returns {"pageviews": {"value": n}, ...}; newer builds return plain numbers."""
    def val(k):
        v = raw.get(k, 0)
        return v.get("value", 0) if isinstance(v, dict) else (v or 0)
    return {k: val(k) for k in ("pageviews", "visitors", "visits", "bounces")}
