"""Read web-analytics totals from a self-hosted Umami instance.

Uses Umami's REST API: POST /api/auth/login, then
GET /api/websites/{id}/stats?startAt=<ms>&endAt=<ms> and
GET /api/websites/{id}/metrics?type=referrer|country|browser|device&startAt=<ms>&endAt=<ms>.
The RFP's web metrics (page views, unique visitors, referrers, session duration, bounce
rate, country, device and browser) all come from these two endpoints; web_summary()
turns them into one tenant-ready object. Not verified against a live Umami yet.
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

    def metric(self, website_id: str, kind: str, start_ms: int, end_ms: int, limit: int = 10) -> list[dict]:
        raw = self._get(f"/api/websites/{website_id}/metrics?type={kind}&startAt={start_ms}&endAt={end_ms}&limit={limit}")
        return normalize_metric(raw)

    def summary(self, website_id: str, start_ms: int, end_ms: int) -> dict:
        kinds = ("referrer", "country", "browser", "device")
        return web_summary(self.stats(website_id, start_ms, end_ms),
                           {k: self.metric(website_id, k, start_ms, end_ms) for k in kinds})


def normalize_stats(raw: dict) -> dict:
    """Umami v2 returns {"pageviews": {"value": n}, ...}; newer builds return plain numbers."""
    def val(k):
        v = raw.get(k, 0)
        return v.get("value", 0) if isinstance(v, dict) else (v or 0)
    return {k: val(k) for k in ("pageviews", "visitors", "visits", "bounces", "totaltime")}


def normalize_metric(raw) -> list[dict]:
    """Umami returns [{"x": "google.com", "y": 120}, ...]; accept {"name","value"} too. Empty names become "(direct / unknown)"."""
    out = []
    for r in raw or []:
        name = r.get("x", r.get("name"))
        out.append({"name": name or "(direct / unknown)", "count": int(r.get("y", r.get("value", 0)) or 0)})
    return sorted(out, key=lambda r: -r["count"])


def web_summary(stats: dict, metrics: dict[str, list[dict]]) -> dict:
    """The RFP's web metrics: page views, unique visitors, referrers, session duration, bounce rate, country, device, browser."""
    visits = stats.get("visits", 0)
    return {
        "pageviews": stats.get("pageviews", 0),
        "visitors": stats.get("visitors", 0),
        "visits": visits,
        "bounce_rate": round(stats.get("bounces", 0) / visits, 4) if visits else 0.0,
        "avg_session_s": round(stats.get("totaltime", 0) / visits, 1) if visits else 0.0,
        "referrers": metrics.get("referrer", []),
        "countries": metrics.get("country", []),
        "browsers": metrics.get("browser", []),
        "devices": metrics.get("device", []),
    }
