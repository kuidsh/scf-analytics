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
from scfa.rollup import EDGES, bucket_of  # noqa: E402
from scfa.umami import normalize_metric, normalize_stats, web_summary  # noqa: E402
from scfa.store import Store  # noqa: E402

random.seed(46)
NOW = int(time.time())
DAYS = 30  # last 30 days go through the real ingest path (raw rows + rollups)
YEAR_DAYS = 365  # days 31..365 are seeded straight into the hourly rollup table (aggregates only)
RANGES = (1, 6, 12, 24, 168, 720, 8760)  # hours: 1 h, 6 h, 12 h, 1 d, 7 d, 30 d, 1 y
PROJECTS = [
    ("example-anchor", "Example Anchor (SEP-24)", ["/sep24/info", "/sep24/transactions/deposit/interactive", "/sep10/auth", "/sep12/customer"], 900, 0.006),
    ("example-wallet", "Example Wallet API", ["/v1/balances", "/v1/quote", "/v1/submit"], 1400, 0.012),
    ("example-soroban", "Example Soroban dApp", ["/rpc/simulateTransaction", "/rpc/sendTransaction", "/rpc/getEvents", "/horizon/accounts/{id}"], 700, 0.01),
    ("example-oracle", "Example Price Oracle", ["/prices/latest", "/prices/history"], 500, 0.035),
]


def span(route, status, ms, t):
    s = t * 1_000_000_000
    return {"name": route, "kind": 2, "startTimeUnixNano": str(s), "endTimeUnixNano": str(s + int(ms * 1e6)),
            "attributes": [{"key": "http.route", "value": {"stringValue": route}},
                           {"key": "http.request.method", "value": {"stringValue": "POST" if "submit" in route or "auth" in route or "/rpc/" in route else "GET"}},
                           {"key": "http.response.status_code", "value": {"intValue": str(status)}}]}


def seed_older_rollups(store, pid, routes, per_hour, err):
    """Days 31..365: aggregate counts only, one row per day/route/status/latency bucket (no raw rows exist this old)."""
    roll = {}
    for d in range(YEAR_DAYS, DAYS, -1):
        day = (NOW - d * 86400) // 86400 * 86400
        scale = 0.55 + 0.45 * (YEAR_DAYS - d) / YEAR_DAYS  # traffic grew over the year
        for r in routes:
            n = int(per_hour * 24 * scale / len(routes) * random.uniform(0.8, 1.2))
            mu = 3.4 if "interactive" not in r else 4.6
            sample = [bucket_of(random.lognormvariate(mu, 0.55)) for _ in range(60)]
            for status_cls, share in ((5, err), (4, 0.02), (2, 1 - err - 0.02)):
                for b in set(sample):
                    c = int(n * share * sample.count(b) / len(sample))
                    if c:
                        roll[(pid, r, "POST" if "submit" in r or "auth" in r or "/rpc/" in r else "GET", status_cls, day, b)] = c
    store.add_rollups(roll)


def web_example(pid, hrs):
    """Example web-analytics numbers shaped exactly like Umami's REST responses, then run through the real
    normalizer and summary code. Not read from a live Umami."""
    rnd = random.Random(f"{pid}-{hrs}")
    base = {"example-anchor": 3200, "example-wallet": 9100, "example-soroban": 2400, "example-oracle": 800}[pid] / 24 * hrs
    visits = int(base * rnd.uniform(.92, 1.08)); visitors = int(visits * .78); views = int(visits * rnd.uniform(2.1, 2.9))
    raw = {"pageviews": {"value": views}, "visitors": {"value": visitors}, "visits": {"value": visits},
           "bounces": {"value": int(visits * rnd.uniform(.32, .48))}, "totaltime": {"value": int(visits * rnd.uniform(95, 190))}}
    def split(names):
        w = [rnd.uniform(.4, 1) ** 2 for _ in names]
        return [{"x": n, "y": int(visits * x / sum(w))} for n, x in zip(names, w)]
    metrics = {"referrer": split(["", "stellar.org", "github.com", "x.com", "reddit.com"]),
               "country": split(["US", "MX", "BR", "NG", "PH", "DE"]),
               "browser": split(["chrome", "safari", "firefox", "edge"]),
               "device": split(["desktop", "mobile", "tablet"])}
    return web_summary(normalize_stats(raw), {k: normalize_metric(v) for k, v in metrics.items()})


def main():
    store = Store(":memory:")
    import os
    os.environ["ADMIN_TOKEN"] = "demo"
    out = {"generated_at": NOW, "projects": {}, "ranges": {}}
    keys = {}
    for pid, name, routes, per_hour, err in PROJECTS:
        key = keys[pid] = store.create_project(pid, name)
        for h in range(DAYS * 24 - 1, -1, -1):  # h = hours ago; h=0 is the hour ending now
            hour_load = int(per_hour * (0.6 + 0.4 * abs(12 - (h % 24)) / 12) * random.uniform(0.85, 1.15))
            bad = err * (6 if (pid == "example-oracle" and h in (5, 4)) else 1)
            spans = []
            for _ in range(hour_load):
                r = random.choice(routes)
                status = 500 if random.random() < bad else (404 if random.random() < 0.02 else 200)
                ms = random.lognormvariate(3.4 if "interactive" not in r else 4.6, 0.55)
                spans.append(span(r, status, ms, NOW - h * 3600 - random.randint(0, 3599)))
            body = json.dumps({"resourceSpans": [{"resource": {"attributes": [{"key": "service.name", "value": {"stringValue": pid}}]},
                                                  "scopeSpans": [{"spans": spans}]}]}).encode()
            assert app.handle("POST", "/v1/traces", {"x-scfa-key": key}, {}, body, store)["statusCode"] == 200
        seed_older_rollups(store, pid, routes, per_hour, err)
        store.set_rule(pid, "error_rate", 0.03, 24 * 60)
    for hrs in RANGES:  # every range comes from the real API code path
        q = {"hours": str(hrs)}
        out["ranges"][str(hrs)] = {
            "global": json.loads(app.handle("GET", "/v1/global", {"x-scfa-admin": "demo"}, q, b"", store)["body"]),
            "projects": {pid: json.loads(app.handle("GET", "/v1/metrics", {"x-scfa-key": k}, q, b"", store)["body"])
                         for pid, k in keys.items()},
            "web": {pid: web_example(pid, hrs) for pid in keys},
        }
    out["global"] = out["ranges"]["24"]["global"]
    out["projects"] = out["ranges"]["24"]["projects"]
    out["alerts"] = [{k: a[k] for k in ("project_id", "metric", "value", "threshold", "window_min")} for a in evaluate(store, NOW)]
    Path(__file__).with_name("data.json").write_text(json.dumps(out))
    print("projects:", {k: v["requests"] for k, v in out["projects"].items()}, "alerts:", out["alerts"])


if __name__ == "__main__":
    main()
