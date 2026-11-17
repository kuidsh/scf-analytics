"""Hourly rollups: the long-term, aggregate-only store.

Raw request rows are short-lived (RAW_RETENTION_DAYS). Every ingested request is also
counted into an hourly histogram per (project, normalized route, method, status class,
latency bucket). Rollups hold no trace ids, no span ids and no per-request timestamps,
only counts, so they can be kept for 24 months (ROLLUP_RETENTION_DAYS) and still answer
volume, status-class and latency-percentile questions for month and year views.
Percentiles from a histogram are upper bucket edges: accurate to the bucket width.
"""
from __future__ import annotations

import math
from collections import Counter, defaultdict

from .metrics import protocol_for, slo

# Latency bucket upper edges in ms; the last bucket is "slower than the final edge".
EDGES = (5, 10, 25, 50, 100, 250, 500, 1000, 2500, 5000, 10000)


def bucket_of(duration_ms: float) -> int:
    for i, e in enumerate(EDGES):
        if duration_ms <= e:
            return i
    return len(EDGES)


def status_class(status: int) -> int:
    return status // 100 if 100 <= status < 600 else 0


def hist_percentile(counts: dict[int, int], p: float) -> float:
    """Nearest-rank percentile over a {bucket: count} histogram (returns the bucket's upper edge)."""
    n = sum(counts.values())
    if not n:
        return 0.0
    rank = max(1, math.ceil(p / 100 * n))
    seen = 0
    for b in sorted(counts):
        seen += counts[b]
        if seen >= rank:
            return float(EDGES[min(b, len(EDGES) - 1)])
    return float(EDGES[-1])


def _pcts(entries):
    h: dict[int, int] = Counter()
    for e in entries:
        h[e[5]] += e[6]
    return h


def summarize_hist(entries) -> dict:
    """entries: (project_id, route, method, status_class, hour, bucket, count). Same shape as metrics.summarize."""
    total = sum(e[6] for e in entries)
    if not total:
        return {"requests": 0, "error_rate": 0.0, "p50_ms": 0.0, "p95_ms": 0.0, "p99_ms": 0.0,
                "status_classes": {}, "routes": [], "protocols": [], "slo": slo(0.0, 0)}
    errors = sum(e[6] for e in entries if e[3] == 5)
    classes = Counter()
    for e in entries:
        classes[f"{e[3]}xx"] += e[6]
    by_route, by_proto = defaultdict(list), defaultdict(list)
    for e in entries:
        by_route[(e[2], e[1])].append(e)
        by_proto[protocol_for(e[1])].append(e)

    def line(es):
        n = sum(x[6] for x in es)
        return n, round(sum(x[6] for x in es if x[3] == 5) / n, 4), hist_percentile(_pcts(es), 95)

    routes = []
    for (method, route), es in by_route.items():
        n, er, p95 = line(es)
        routes.append({"method": method, "route": route, "protocol": protocol_for(route),
                       "requests": n, "error_rate": er, "p95_ms": p95})
    routes.sort(key=lambda x: -x["requests"])
    protocols = []
    for name, es in by_proto.items():
        n, er, p95 = line(es)
        protocols.append({"protocol": name, "requests": n, "error_rate": er, "p95_ms": p95})
    protocols.sort(key=lambda x: -x["requests"])
    h = _pcts(entries)
    er = round(errors / total, 4)
    return {"requests": total, "error_rate": er, "p50_ms": hist_percentile(h, 50),
            "p95_ms": hist_percentile(h, 95), "p99_ms": hist_percentile(h, 99),
            "status_classes": dict(sorted(classes.items())), "routes": routes,
            "protocols": protocols, "slo": slo(er, total)}


def timeseries_hist(entries, bucket_s: int = 3600) -> list[dict]:
    b = defaultdict(lambda: [0, 0])
    for e in entries:
        k = e[4] - e[4] % bucket_s
        b[k][0] += e[6]
        b[k][1] += e[6] if e[3] == 5 else 0
    return [{"t": k, "requests": v[0], "errors": v[1]} for k, v in sorted(b.items())]


def global_view_hist(entries, projects) -> dict:
    per = defaultdict(list)
    for e in entries:
        per[e[0]].append(e)
    lines = []
    for p in projects:
        s = summarize_hist(per.get(p["id"], []))
        lines.append({"project": p["id"], "name": p["name"], "requests": s["requests"],
                      "error_rate": s["error_rate"], "p95_ms": s["p95_ms"]})
    t = summarize_hist(entries)
    return {"projects": lines, "requests": t["requests"], "error_rate": t["error_rate"],
            "p95_ms": t["p95_ms"], "active_projects": sum(1 for x in lines if x["requests"])}
