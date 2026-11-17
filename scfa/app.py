"""HTTP API. Runs as an AWS Lambda (API Gateway HTTP API v2 events) or locally.

Routes
  POST /v1/traces                 OTLP/HTTP JSON; header x-scfa-key: <project key>
  GET  /v1/metrics?hours=24       project view (same key)
  GET  /v1/global?hours=24        SCF-wide view; header x-scfa-admin: <ADMIN_TOKEN>
  GET  /healthz
"""
from __future__ import annotations

import base64
import hmac
import json
import os
import time

from .metrics import global_view, summarize, timeseries
from .otlp import parse_traces
from .store import Store

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
        return max(1, min(24 * 30, int(q.get("hours", 24))))
    except (TypeError, ValueError):
        return 24


def handle(method: str, path: str, headers: dict, query: dict, body: bytes, store: Store | None = None):
    store = store or get_store()
    headers = {k.lower(): v for k, v in (headers or {}).items()}
    now = int(time.time())

    if path == "/healthz":
        return _resp(200, {"ok": True})

    if path == "/v1/global" and method == "GET":
        admin = os.environ.get("ADMIN_TOKEN", "")
        if not admin or not hmac.compare_digest(headers.get("x-scfa-admin", ""), admin):
            return _resp(401, {"error": "Admin token missing or wrong."})
        rows = store.requests_since(None, now - _hours(query) * 3600)
        return _resp(200, global_view(rows, store.projects()))

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
        rows = store.requests_since(project["id"], now - _hours(query) * 3600)
        return _resp(200, {"project": project, **summarize(rows), "series": timeseries(rows)})

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
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(r["body"].encode())
        do_GET = do_POST = _go

    port = int(os.environ.get("PORT", 8080))
    print(f"SCF Analytics API on http://localhost:{port}")
    HTTPServer(("0.0.0.0", port), H).serve_forever()
