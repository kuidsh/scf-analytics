import json
import time

import pytest

from scfa import app
from scfa.alerts import evaluate
from scfa.metrics import bucket_for, percentile, protocol_for, slo, summarize
from scfa.otlp import ApiRequest, normalize_path, parse_traces
from scfa.store import Store
from scfa.umami import normalize_metric, normalize_stats, web_summary


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


def test_time_ranges_filter_and_bucket(store):
    key = store.create_project("p", "P")
    now = int(time.time())
    # one request 30 min ago, one 5 h ago, one 3 days ago, one 20 days ago
    for age_h in (0.5, 5, 72, 480):
        t = (now - int(age_h * 3600)) * 1_000_000_000
        span = {"kind": 2, "startTimeUnixNano": str(t), "endTimeUnixNano": str(t + 10_000_000),
                "attributes": [{"key": "http.response.status_code", "value": {"intValue": "200"}}]}
        body = json.dumps({"resourceSpans": [{"scopeSpans": [{"spans": [span]}]}]}).encode()
        assert app.handle("POST", "/v1/traces", {"x-scfa-key": key}, {}, body, store)["statusCode"] == 200

    def n(hours):
        r = app.handle("GET", "/v1/metrics", {"x-scfa-key": key}, {"hours": str(hours)}, b"", store)
        return json.loads(r["body"])["requests"]

    assert [n(h) for h in (1, 6, 12, 24, 168, 720, 8760)] == [1, 2, 2, 2, 3, 4, 4]
    assert [bucket_for(h) for h in (1, 6, 12, 168, 720, 8760)] == [300, 300, 3600, 3600, 21600, 86400]
    assert n(999999) == 4  # clamped to one year, not an error


def test_protocol_slo_and_csv_export(store):
    assert [protocol_for(r) for r in ("/sep10/auth", "/sep24/info", "/sep31/send", "/rpc/getEvents", "/horizon/accounts/G1", "/v1/x")] == [
        "SEP-10 auth", "SEP-24 deposit/withdraw", "SEP-31 payments", "Soroban RPC", "Horizon", "Other"]
    assert slo(0.002, 1000)["met"] and slo(0.002, 1000)["budget_used"] == 0.4
    assert not slo(0.01, 1000)["met"] and slo(0.01, 1000)["budget_used"] == 2.0
    assert slo(0.0, 0)["budget_used"] == 0.0

    key = store.create_project("p", "P")
    t = int(time.time()) * 1_000_000_000
    def span(route, status):
        return {"kind": 2, "startTimeUnixNano": str(t), "endTimeUnixNano": str(t + 20_000_000),
                "attributes": [{"key": "http.route", "value": {"stringValue": route}},
                               {"key": "http.response.status_code", "value": {"intValue": str(status)}}]}
    spans = [span("/sep10/auth", 200)] * 3 + [span("/rpc/getEvents", 500)]
    body = json.dumps({"resourceSpans": [{"scopeSpans": [{"spans": spans}]}]}).encode()
    app.handle("POST", "/v1/traces", {"x-scfa-key": key}, {}, body, store)

    m = json.loads(app.handle("GET", "/v1/metrics", {"x-scfa-key": key}, {}, b"", store)["body"])
    assert {p["protocol"]: p["requests"] for p in m["protocols"]} == {"SEP-10 auth": 3, "Soroban RPC": 1}
    assert m["slo"]["met"] is False
    r = app.handle("GET", "/v1/metrics", {"x-scfa-key": key}, {"format": "csv"}, b"", store)
    assert r["headers"]["Content-Type"].startswith("text/csv")
    lines = r["body"].strip().splitlines()
    assert lines[0] == "method,route,protocol,requests,error_rate_5xx,p95_ms" and len(lines) == 3
    # CSV is still tenant-scoped
    assert app.handle("GET", "/v1/metrics", {"x-scfa-key": "bad"}, {"format": "csv"}, b"", store)["statusCode"] == 401


def test_path_normalization_hides_ids_and_addresses(store):
    acct = "G" + "A" * 55
    assert normalize_path(f"/accounts/{acct}/payments?cursor=abc") == "/accounts/{account}/payments"
    assert normalize_path("/tx/" + "ab" * 32) == "/tx/{hash}"
    assert normalize_path("/u/42/o/550e8400-e29b-41d4-a716-446655440000") == "/u/{id}/o/{uuid}"
    assert normalize_path("/sep24/info") == "/sep24/info" and normalize_path("/accounts/{id}") == "/accounts/{id}"
    # end to end: the stored route never contains the address
    key = store.create_project("p", "P")
    t = int(time.time()) * 1_000_000_000
    span = {"kind": 2, "startTimeUnixNano": str(t), "endTimeUnixNano": str(t + 1_000_000),
            "attributes": [{"key": "url.path", "value": {"stringValue": f"/accounts/{acct}"}},
                           {"key": "http.response.status_code", "value": {"intValue": "200"}}]}
    body = json.dumps({"resourceSpans": [{"scopeSpans": [{"spans": [span]}]}]}).encode()
    app.handle("POST", "/v1/traces", {"x-scfa-key": key}, {}, body, store)
    m = json.loads(app.handle("GET", "/v1/metrics", {"x-scfa-key": key}, {}, b"", store)["body"])
    assert [r["route"] for r in m["routes"]] == ["/accounts/{account}"]


def test_rollups_outlive_raw_rows_and_serve_long_windows(store):
    key = store.create_project("p", "P")
    now = int(time.time())
    old = now - 100 * 86400  # older than the 30-day raw retention
    store.insert_requests("p", [ApiRequest("s", "/sep24/info", "GET", 200 if i else 503, 40.0 + i, old) for i in range(20)])
    store.insert_requests("p", [ApiRequest("s", "/sep24/info", "GET", 200, 10.0, now)])
    assert store.purge_raw(now) == 20  # raw rows older than 30 days are gone...
    year = json.loads(app.handle("GET", "/v1/metrics", {"x-scfa-key": key}, {"hours": "8760"}, b"", store)["body"])
    assert year["source"] == "rollup" and year["requests"] == 21  # ...but the aggregates remain
    assert year["status_classes"] == {"2xx": 20, "5xx": 1} and year["routes"][0]["protocol"] == "SEP-24 deposit/withdraw"
    assert year["p95_ms"] in (50.0, 100.0)  # histogram edge, not an exact value
    month = json.loads(app.handle("GET", "/v1/metrics", {"x-scfa-key": key}, {"hours": "720"}, b"", store)["body"])
    assert month["source"] == "raw" and month["requests"] == 1
    assert not any("trace" in c.lower() or "span" in c.lower()
                   for c in [r[1] for r in store._exec("PRAGMA table_info(api_rollups)").fetchall()])
    store.purge_raw(now + 800 * 86400)  # 24 months later even the rollups expire
    assert store.rollups_since(None, 0) == []


def test_self_service_enrollment_and_operator_controls(store, monkeypatch):
    monkeypatch.setenv("ADMIN_TOKEN", "adm")
    call = lambda m, p, h=None, b=b"": app.handle(m, p, h or {}, {}, b, store)
    enroll = lambda pid: call("POST", "/v1/enroll", b=json.dumps({"id": pid, "name": "X"}).encode())
    r = enroll("my-anchor"); assert r["statusCode"] == 201
    key = json.loads(r["body"])["key"]
    assert enroll("my-anchor")["statusCode"] == 409 and enroll("Bad ID!")["statusCode"] == 400
    assert call("GET", "/v1/metrics", {"x-scfa-key": key})["statusCode"] == 200
    adm = {"x-scfa-admin": "adm"}
    assert call("GET", "/v1/admin/projects")["statusCode"] == 401
    assert len(json.loads(call("GET", "/v1/admin/projects", adm)["body"])["projects"]) == 1
    new = json.loads(call("POST", "/v1/admin/projects/my-anchor/rotate-key", adm)["body"])["key"]
    assert call("GET", "/v1/metrics", {"x-scfa-key": key})["statusCode"] == 401  # old key is dead
    assert call("GET", "/v1/metrics", {"x-scfa-key": new})["statusCode"] == 200
    assert call("POST", "/v1/admin/projects/my-anchor/revoke-key", adm)["statusCode"] == 200
    assert call("GET", "/v1/metrics", {"x-scfa-key": new})["statusCode"] == 401  # revoked, none issued
    assert call("DELETE", "/v1/admin/projects/my-anchor", adm)["statusCode"] == 200
    assert call("DELETE", "/v1/admin/projects/my-anchor", adm)["statusCode"] == 404
    assert json.loads(call("GET", "/v1/admin/projects", adm)["body"])["projects"] == []
    monkeypatch.setenv("ENROLLMENT", "closed")
    assert enroll("another")["statusCode"] == 403


def test_web_summary_has_every_rfp_web_metric():
    stats = normalize_stats({"pageviews": {"value": 1000}, "visitors": {"value": 400}, "visits": {"value": 500},
                             "bounces": {"value": 200}, "totaltime": {"value": 60000}})
    m = {"referrer": normalize_metric([{"x": "", "y": 5}, {"x": "stellar.org", "y": 9}]),
         "country": normalize_metric([{"x": "MX", "y": 3}]), "browser": normalize_metric([{"name": "chrome", "value": 7}]),
         "device": normalize_metric([{"x": "desktop", "y": 4}])}
    w = web_summary(stats, m)
    assert (w["pageviews"], w["visitors"], w["bounce_rate"], w["avg_session_s"]) == (1000, 400, 0.4, 120.0)
    assert w["referrers"][0] == {"name": "stellar.org", "count": 9} and w["referrers"][1]["name"].startswith("(direct")
    assert w["countries"][0]["name"] == "MX" and w["browsers"][0]["count"] == 7 and w["devices"][0]["name"] == "desktop"
    assert web_summary({}, {})["bounce_rate"] == 0.0  # no visits: no division by zero
