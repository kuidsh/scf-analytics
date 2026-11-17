"""Generate example traffic for 3 made-up Stellar projects, run it through the
real pipeline (parse -> store -> metrics -> alerts) and write demo/data.json.
All projects and numbers are EXAMPLES, not real ecosystem data."""
import json
import random
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scfa import app  # noqa: E402
from scfa.alerts import evaluate  # noqa: E402
from scfa.store import Store  # noqa: E402

random.seed(46)
NOW = int(time.time()) // 3600 * 3600
PROJECTS = [
    ("example-anchor", "Example Anchor (SEP-24)", ["/sep24/info", "/sep24/transactions/deposit/interactive", "/sep10/auth", "/sep12/customer"], 900, 0.006),
    ("example-wallet", "Example Wallet API", ["/v1/balances", "/v1/quote", "/v1/submit"], 1400, 0.012),
    ("example-oracle", "Example Price Oracle", ["/prices/latest", "/prices/history"], 500, 0.035),
]


def span(route, status, ms, t):
    s = t * 1_000_000_000
    return {"name": route, "kind": 2, "startTimeUnixNano": str(s), "endTimeUnixNano": str(s + int(ms * 1e6)),
            "attributes": [{"key": "http.route", "value": {"stringValue": route}},
                           {"key": "http.request.method", "value": {"stringValue": "POST" if "submit" in route or "auth" in route else "GET"}},
                           {"key": "http.response.status_code", "value": {"intValue": str(status)}}]}


def main():
    store = Store(":memory:")
    import os
    os.environ["ADMIN_TOKEN"] = "demo"
    out = {"generated_at": NOW, "projects": {}}
    for pid, name, routes, per_hour, err in PROJECTS:
        key = store.create_project(pid, name)
        for h in range(24, 0, -1):
            hour_load = int(per_hour * (0.6 + 0.4 * abs(12 - (h % 24)) / 12) * random.uniform(0.85, 1.15))
            bad = err * (6 if (pid == "example-oracle" and h in (5, 4)) else 1)
            spans = []
            for _ in range(hour_load):
                r = random.choice(routes)
                status = 500 if random.random() < bad else (404 if random.random() < 0.02 else 200)
                ms = random.lognormvariate(3.4 if "interactive" not in r else 4.6, 0.55)
                spans.append(span(r, status, ms, NOW - h * 3600 + random.randint(0, 3599)))
            body = json.dumps({"resourceSpans": [{"resource": {"attributes": [{"key": "service.name", "value": {"stringValue": pid}}]},
                                                  "scopeSpans": [{"spans": spans}]}]}).encode()
            assert app.handle("POST", "/v1/traces", {"x-scfa-key": key}, {}, body, store)["statusCode"] == 200
        m = json.loads(app.handle("GET", "/v1/metrics", {"x-scfa-key": key}, {}, b"", store)["body"])
        out["projects"][pid] = m
        store.set_rule(pid, "error_rate", 0.03, 24 * 60)
    out["global"] = json.loads(app.handle("GET", "/v1/global", {"x-scfa-admin": "demo"}, {}, b"", store)["body"])
    out["alerts"] = [{k: a[k] for k in ("project_id", "metric", "value", "threshold")} for a in evaluate(store, NOW)]
    Path(__file__).with_name("data.json").write_text(json.dumps(out))
    print("projects:", {k: v["requests"] for k, v in out["projects"].items()}, "alerts:", out["alerts"])


if __name__ == "__main__":
    main()
