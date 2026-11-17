"""HTTP API. Runs as an AWS Lambda (API Gateway HTTP API v2 events) or locally.

Routes
  POST /v1/traces                 OTLP/HTTP JSON; header x-scfa-key: <project key>
  GET  /v1/metrics?hours=24[&format=csv]  project view (csv = per-route export) (same key); hours 1..8760 (1h, 6h, 12h, 24h, 168=7d, 720=30d, 8760=1y)
  GET  /v1/global?hours=24        SCF-wide view; header x-scfa-admin: <ADMIN_TOKEN>
  POST /v1/enroll                 sign-up {"id","name"}; returns the project key once. CLOSED by default.
                                  ENROLLMENT=closed (default): only an operator (x-scfa-admin) can enroll.
                                  ENROLLMENT=invite: header x-scfa-invite must match a code in ENROLL_INVITES
                                  (comma-separated). ENROLLMENT=open: anyone. In invite and open modes at most
                                  ENROLL_MAX_PER_HOUR (default 10) projects are created per hour (429 after that).
  GET  /v1/admin/projects                       operator: list projects          (x-scfa-admin)
  POST /v1/admin/projects/<id>/rotate-key       operator: new key, old one dies  (x-scfa-admin)
  POST /v1/admin/projects/<id>/revoke-key       operator: key dies, none issued  (x-scfa-admin)
  DELETE /v1/admin/projects/<id>                operator: remove project and ALL its data (x-scfa-admin)
  GET  /healthz
Windows up to 30 days read exact raw rows; longer windows read the hourly rollups (24 months).
"""
from __future__ import annotations

import base64
import csv
import hmac
import io
import json
import os
import re
import time

from .metrics import bucket_for, global_view, summarize, timeseries
from .otlp import parse_traces
from .rollup import global_view_hist, summarize_hist, timeseries_hist
from .store import RAW_RETENTION_DAYS, Store

PROJECT_ID = re.compile(r"^[a-z0-9][a-z0-9-]{2,39}$")

MAX_BODY = 5 * 1024 * 1024
_store: Store | None = None


def get_store() -> Store:
    global _store
    if _store is None:
        _store = Store()
    return _store


def _resp(status: int, body: dict):
    return {"statusCode": status, "headers": {"Content-Type": "application/json"},
            "body": json.dumps(body)}


def _hours(q: dict) -> int:
    try:
        return max(1, min(24 * 365, int(q.get("hours", 24))))
    except (TypeError, ValueError):
        return 24


def handle(method: str, path: str, headers: dict, query: dict, body: bytes, store: Store | None = None):
    store = store or get_store()
    headers = {k.lower(): v for k, v in (headers or {}).items()}
    now = int(time.time())

    if path == "/healthz":
        return _resp(200, {"ok": True})

    admin = os.environ.get("ADMIN_TOKEN", "")
    is_admin = bool(admin) and hmac.compare_digest(headers.get("x-scfa-admin", ""), admin)
    hours = _hours(query)
    long_window = hours > RAW_RETENTION_DAYS * 24  # raw rows are gone; use the aggregate rollups

    if path == "/v1/global" and method == "GET":
        if not is_admin:
            return _resp(401, {"error": "Admin token missing or wrong."})
        if long_window:
            view = global_view_hist(store.rollups_since(None, now - hours * 3600), store.projects())
        else:
            view = global_view(store.requests_since(None, now - hours * 3600), store.projects())
        return _resp(200, {**view, "source": "rollup" if long_window else "raw"})

    if path == "/v1/enroll" and method == "POST":  # self-service; SCF removes non-ecosystem projects
        mode = os.environ.get("ENROLLMENT", "closed")
        if not is_admin:  # operators can always create tenants; everyone else goes through the gate
            if mode == "invite":
                codes = [c.strip() for c in os.environ.get("ENROLL_INVITES", "").split(",") if c.strip()]
                given = headers.get("x-scfa-invite", "")
                if not any(hmac.compare_digest(given, c) for c in codes):
                    return _resp(403, {"error": "A valid invite code is required (header x-scfa-invite)."})
            elif mode != "open":
                return _resp(403, {"error": "Enrollment is closed. Ask an SCF operator to create your project."})
            try:
                cap = int(os.environ.get("ENROLL_MAX_PER_HOUR", "10"))
            except ValueError:
                cap = 10
            if store.projects_created_since(now - 3600) >= cap:
                return _resp(429, {"error": "Too many enrollments this hour. Try again later."})
        try:
            req = json.loads(body or b"{}")
            pid, name = str(req["id"]), str(req["name"]).strip()
        except (ValueError, KeyError, TypeError):
            return _resp(400, {"error": 'Send JSON like {"id": "my-anchor", "name": "My Anchor"}.'})
        if not PROJECT_ID.match(pid) or not 1 <= len(name) <= 80:
            return _resp(400, {"error": "id: 3-40 chars, lowercase letters, digits and dashes; name: 1-80 chars."})
        if any(p["id"] == pid for p in store.projects()):
            return _resp(409, {"error": "That project id is taken."})
        return _resp(201, {"id": pid, "name": name, "key": store.create_project(pid, name),
                           "note": "Store this key now; it is shown once and kept only as a hash."})

    if path.startswith("/v1/admin/"):
        if not is_admin:
            return _resp(401, {"error": "Admin token missing or wrong."})
        parts = path.split("/")[3:]  # ["projects", "<id>", "rotate-key"]
        if parts == ["projects"] and method == "GET":
            return _resp(200, {"projects": store.projects()})
        if len(parts) >= 2 and parts[0] == "projects":
            pid = parts[1]
            if len(parts) == 3 and parts[2] == "rotate-key" and method == "POST":
                key = store.rotate_key(pid)
                return _resp(200, {"id": pid, "key": key}) if key else _resp(404, {"error": "No such project."})
            if len(parts) == 3 and parts[2] == "revoke-key" and method == "POST":
                return _resp(200, {"id": pid, "revoked": True}) if store.revoke_key(pid) else _resp(404, {"error": "No such project."})
            if len(parts) == 2 and method == "DELETE":
                return _resp(200, {"id": pid, "deleted": True}) if store.delete_project(pid) else _resp(404, {"error": "No such project."})
        return _resp(404, {"error": "No such route."})

    project = store.project_for_key(headers.get("x-scfa-key"))
    if project is None:
        return _resp(401, {"error": "Project key missing or wrong. Send it in the x-scfa-key header."})

    if path == "/v1/traces" and method == "POST":
        if len(body) > MAX_BODY:
            return _resp(413, {"error": "Batch too large; send at most 5 MB per request."})
        if "protobuf" in headers.get("content-type", ""):
            return _resp(415, {"error": "Send OTLP as JSON (set the exporter protocol to http/json)."})
        try:
            reqs = parse_traces(json.loads(body or b"{}"))
        except (ValueError, KeyError, TypeError) as e:
            return _resp(400, {"error": f"Not a valid OTLP JSON trace payload: {e}"})
        n = store.insert_requests(project["id"], reqs)
        return _resp(200, {"accepted": n, "partialSuccess": {}})

    if path == "/v1/metrics" and method == "GET":
        if long_window:
            entries = store.rollups_since(project["id"], now - hours * 3600)
            s, series = summarize_hist(entries), timeseries_hist(entries, bucket_for(hours))
        else:
            rows = store.requests_since(project["id"], now - hours * 3600)
            s, series = summarize(rows), timeseries(rows, bucket_for(hours))
        if query.get("format") == "csv":  # per-route export for spreadsheets
            buf = io.StringIO()
            w = csv.writer(buf)
            w.writerow(["method", "route", "protocol", "requests", "error_rate_5xx", "p95_ms"])
            for r in s["routes"]:
                w.writerow([r["method"], r["route"], r["protocol"], r["requests"], r["error_rate"], r["p95_ms"]])
            return {"statusCode": 200, "headers": {"Content-Type": "text/csv; charset=utf-8",
                    "Content-Disposition": f'attachment; filename="{project["id"]}-routes.csv"'}, "body": buf.getvalue()}
        return _resp(200, {"project": project, **s, "series": series, "source": "rollup" if long_window else "raw"})

    return _resp(404, {"error": "No such route."})


def lambda_handler(event, _context):
    """API Gateway HTTP API (payload v2) entry point."""
    rc = event.get("requestContext", {}).get("http", {})
    body = event.get("body") or ""
    raw = base64.b64decode(body) if event.get("isBase64Encoded") else body.encode()
    return handle(rc.get("method", "GET"), event.get("rawPath", "/"), event.get("headers", {}),
                  event.get("queryStringParameters") or {}, raw)


def alerts_handler(_event, _context):
    """Scheduled (EventBridge, every 5 min): evaluate rules, notify, purge old raw rows."""
    from .alerts import evaluate, notify
    store = get_store()
    fired = evaluate(store)
    sent = sum(notify(a) for a in fired)
    purged = store.purge_raw()
    return {"fired": len(fired), "sent": sent, "purged": purged}


if __name__ == "__main__":  # local dev server: python -m scfa.app
    from http.server import BaseHTTPRequestHandler, HTTPServer
    from urllib.parse import parse_qsl, urlsplit

    class H(BaseHTTPRequestHandler):
        def _go(self):
            u = urlsplit(self.path)
            n = int(self.headers.get("Content-Length") or 0)
            r = handle(self.command, u.path, dict(self.headers), dict(parse_qsl(u.query)), self.rfile.read(n))
            self.send_response(r["statusCode"])
            for k, v in r.get("headers", {"Content-Type": "application/json"}).items():
                self.send_header(k, v)
            self.end_headers()
            self.wfile.write(r["body"].encode())
        do_GET = do_POST = do_DELETE = _go

    port = int(os.environ.get("PORT", 8080))
    print(f"SCF Analytics API on http://localhost:{port}")
    HTTPServer(("0.0.0.0", port), H).serve_forever()
