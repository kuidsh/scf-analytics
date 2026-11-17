import json
import time

import pytest

from scfa import app
from scfa.alerts import evaluate
from scfa.metrics import percentile, summarize
from scfa.otlp import parse_traces
from scfa.store import Store
from scfa.umami import normalize_stats


def span(route, status, ms, start_s, kind=2, method="GET", old_names=False):
    start = start_s * 1_000_000_000
    keys = ("http.target", "http.method", "http.status_code") if old_names else \
           ("http.route", "http.request.method", "http.response.status_code")
    return {
        "name": f"{method} {route}", "kind": kind,
        "startTimeUnixNano": str(start), "endTimeUnixNano": str(start + int(ms * 1e6)),
        "attributes": [
            {"key": keys[0], "value": {"stringValue": route}},
            {"key": keys[1], "value": {"stringValue": method}},
            {"key": keys[2], "value": {"intValue": str(status)}},
        ],
    }


def payload(spans, service="wallet-api"):
    return {"resourceSpans": [{
        "resource": {"attributes": [{"key": "service.name", "value": {"stringValue": service}}]},
        "scopeSpans": [{"spans": spans}]}]}


@pytest.fixture
def store():
    return Store(":memory:")


def test_parse_keeps_only_server_spans_and_strips_query():
    now = int(time.time())
    reqs = parse_traces(payload([span("/quote?amt=5", 200, 12.5, now),
                                 span("/internal", 200, 1, now, kind=3)]))
    assert len(reqs) == 1
    r = reqs[0]
    assert (r.route, r.status, r.service, r.duration_ms) == ("/quote", 200, "wallet-api", 12.5)


def test_parse_accepts_old_semconv_names():
    r = parse_traces(payload([span("/v1/pay", 503, 40, 100, method="post", old_names=True)]))[0]
    assert (r.route, r.method, r.status) == ("/v1/pay", "POST", 503)


def test_percentile_nearest_rank():
    vals = sorted(float(i) for i in range(1, 101))
    assert percentile(vals, 50) == 50.0
    assert percentile(vals, 95) == 95.0
    assert percentile(vals, 99) == 99.0
    assert percentile([], 95) == 0.0


def test_summarize_status_and_error_rate():
    rows = [("p", "/a", "GET", s, 10.0, 0) for s in (200, 200, 404, 500)]
    s = summarize(rows)
    assert s["requests"] == 4
    assert s["error_rate"] == 0.25          # only 5xx count as errors
    assert s["status_classes"] == {"2xx": 2, "4xx": 1, "5xx": 1}


def test_api_ingest_and_metrics_are_tenant_isolated(store):
    key_a = store.create_project("anchor-a", "Anchor A")
    key_b = store.create_project("wallet-b", "Wallet B")
    now = int(time.time())
    body = json.dumps(payload([span("/sep24/info", 200, 30, now), span("/sep24/info", 500, 90, now)])).encode()
    r = app.handle("POST", "/v1/traces", {"X-SCFA-Key": key_a}, {}, body, store)
    assert r["statusCode"] == 200 and json.loads(r["body"])["accepted"] == 2

    ma = json.loads(app.handle("GET", "/v1/metrics", {"x-scfa-key": key_a}, {}, b"", store)["body"])
    mb = json.loads(app.handle("GET", "/v1/metrics", {"x-scfa-key": key_b}, {}, b"", store)["body"])
    assert ma["requests"] == 2 and ma["error_rate"] == 0.5
    assert mb["requests"] == 0


def test_api_rejects_bad_key_and_protobuf(store):
    assert app.handle("GET", "/v1/metrics", {"x-scfa-key": "nope"}, {}, b"", store)["statusCode"] == 401
    key = store.create_project("p", "P")
    r = app.handle("POST", "/v1/traces", {"x-scfa-key": key, "content-type": "application/x-protobuf"},
                   {}, b"\x00", store)
    assert r["statusCode"] == 415


def test_global_view_requires_admin(store, monkeypatch):
    monkeypatch.setenv("ADMIN_TOKEN", "s3cret")
    store.create_project("p", "P")
    assert app.handle("GET", "/v1/global", {}, {}, b"", store)["statusCode"] == 401
    r = app.handle("GET", "/v1/global", {"x-scfa-admin": "s3cret"}, {}, b"", store)
    assert r["statusCode"] == 200 and json.loads(r["body"])["projects"][0]["project"] == "p"


def test_alert_rules(store):
    key = store.create_project("p", "P")
    now = int(time.time())
    store.insert_requests("p", parse_traces(payload([span("/x", 500, 5, now - 10)] * 3 +
                                                    [span("/x", 200, 5, now - 10)])))
    store.set_rule("p", "error_rate", 0.10, 5)
    store.set_rule("p", "p95_ms", 1000, 5)
    store.set_rule("p", "requests_min", 100, 5)
    fired = {a["metric"] for a in evaluate(store, now)}
    assert fired == {"error_rate", "requests_min"}


def test_purge_raw(store):
    store.create_project("p", "P")
    now = int(time.time())
    store.insert_requests("p", parse_traces(payload([span("/old", 200, 1, now - 40 * 86400),
                                                     span("/new", 200, 1, now)])))
    assert store.purge_raw(now) == 1


def test_lambda_event_shape(store, monkeypatch):
    monkeypatch.setattr(app, "_store", store)
    ev = {"rawPath": "/healthz", "requestContext": {"http": {"method": "GET"}}}
    assert app.lambda_handler(ev, None)["statusCode"] == 200


def test_umami_stats_both_shapes():
    assert normalize_stats({"pageviews": {"value": 7}, "visitors": {"value": 3}})["pageviews"] == 7
    assert normalize_stats({"pageviews": 9, "visitors": 4})["visitors"] == 4
