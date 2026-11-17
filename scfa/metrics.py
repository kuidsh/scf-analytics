"""Metrics the RFP asks for: request volume, status codes, latency percentiles."""
from __future__ import annotations

import math
from collections import Counter, defaultdict


SLO_TARGET = 0.995  # default availability objective: 99.5% of requests are not 5xx

# Stellar-aware grouping of routes (first match wins). Lets a project see
# SEP-10/12/24/31 anchor traffic, Horizon and Soroban RPC calls separately.
PROTOCOLS = (
    ("SEP-10 auth", ("/sep10", "/.well-known/stellar.toml/auth")),
    ("SEP-12 KYC", ("/sep12",)),
    ("SEP-24 deposit/withdraw", ("/sep24",)),
    ("SEP-31 payments", ("/sep31",)),
    ("Soroban RPC", ("/rpc",)),
    ("Horizon", ("/horizon",)),
)


def protocol_for(route: str) -> str:
    r = (route or "").lower()
    for name, prefixes in PROTOCOLS:
        if any(r.startswith(p) for p in prefixes):
            return name
    return "Other"


def slo(error_rate: float, requests: int, target: float = SLO_TARGET) -> dict:
    """Availability vs objective. budget_used > 1 means the error budget is spent."""
    allowed = 1 - target
    return {"target": target, "availability": round(1 - error_rate, 4),
            "budget_used": round(error_rate / allowed, 2) if requests else 0.0, "met": error_rate <= allowed}


def percentile(sorted_vals: list[float], p: float) -> float:
    """Nearest-rank percentile (p in 0..100) on an already sorted list."""
    if not sorted_vals:
        return 0.0
    k = max(0, min(len(sorted_vals) - 1, math.ceil(p / 100 * len(sorted_vals)) - 1))
    return round(sorted_vals[k], 2)


def summarize(rows) -> dict:
    """rows: (project_id, route, method, status, duration_ms, ts)."""
    if not rows:
        return {"requests": 0, "error_rate": 0.0, "p50_ms": 0.0, "p95_ms": 0.0, "p99_ms": 0.0,
                "status_classes": {}, "routes": [], "protocols": [], "slo": slo(0.0, 0)}
    durs = sorted(r[4] for r in rows)
    classes = Counter(f"{r[3] // 100}xx" for r in rows)
    errors = sum(1 for r in rows if r[3] >= 500)
    by_route = defaultdict(list)
    for r in rows:
        by_route[(r[2], r[1])].append(r)
    routes = []
    for (method, route), rs in by_route.items():
        d = sorted(x[4] for x in rs)
        routes.append({
            "method": method, "route": route, "protocol": protocol_for(route), "requests": len(rs),
            "error_rate": round(sum(1 for x in rs if x[3] >= 500) / len(rs), 4),
            "p95_ms": percentile(d, 95),
        })
    routes.sort(key=lambda x: -x["requests"])
    by_proto = defaultdict(list)
    for r in rows:
        by_proto[protocol_for(r[1])].append(r)
    protocols = sorted(({
        "protocol": name, "requests": len(rs),
        "error_rate": round(sum(1 for x in rs if x[3] >= 500) / len(rs), 4),
        "p95_ms": percentile(sorted(x[4] for x in rs), 95),
    } for name, rs in by_proto.items()), key=lambda x: -x["requests"])
    return {
        "requests": len(rows),
        "error_rate": round(errors / len(rows), 4),
        "p50_ms": percentile(durs, 50),
        "p95_ms": percentile(durs, 95),
        "p99_ms": percentile(durs, 99),
        "status_classes": dict(sorted(classes.items())),
        "routes": routes,
        "protocols": protocols,
        "slo": slo(round(errors / len(rows), 4), len(rows)),
    }


def bucket_for(hours: int) -> int:
    """Chart bucket size in seconds, so every window gives roughly 70-170 points."""
    if hours <= 6:
        return 300          # 5 min
    if hours <= 168:
        return 3600         # 1 h
    if hours <= 24 * 31:
        return 6 * 3600     # 6 h
    return 86400            # 1 day


def timeseries(rows, bucket_s: int = 3600) -> list[dict]:
    """Requests and 5xx per bucket, for sparkline charts."""
    b = defaultdict(lambda: [0, 0])
    for r in rows:
        k = r[5] - r[5] % bucket_s
        b[k][0] += 1
        b[k][1] += r[3] >= 500
    return [{"t": k, "requests": v[0], "errors": v[1]} for k, v in sorted(b.items())]


def global_view(rows, projects) -> dict:
    """SCF-wide view: totals plus one line per project. No route detail."""
    per = defaultdict(list)
    for r in rows:
        per[r[0]].append(r)
    lines = []
    for p in projects:
        s = summarize(per.get(p["id"], []))
        lines.append({"project": p["id"], "name": p["name"], "requests": s["requests"],
                      "error_rate": s["error_rate"], "p95_ms": s["p95_ms"]})
    total = summarize(rows)
    return {"projects": lines, "requests": total["requests"], "error_rate": total["error_rate"],
            "p95_ms": total["p95_ms"], "active_projects": sum(1 for l in lines if l["requests"])}
