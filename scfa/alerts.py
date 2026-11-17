"""Monitoring and alerting baseline: threshold rules checked on a schedule."""
from __future__ import annotations

import json
import time
import urllib.request

from .metrics import summarize

METRICS = {"error_rate", "p95_ms", "p99_ms", "requests_min"}


def evaluate(store, now: int | None = None) -> list[dict]:
    now = now or int(time.time())
    fired = []
    for rule in store.rules():
        if rule["metric"] not in METRICS:
            continue
        rows = store.requests_since(rule["project_id"], now - rule["window_min"] * 60)
        s = summarize(rows)
        if rule["metric"] == "requests_min":
            # fires when traffic drops BELOW threshold (API looks down)
            value, breach = s["requests"], s["requests"] < rule["threshold"]
        else:
            value = s[rule["metric"]]
            breach = s["requests"] > 0 and value > rule["threshold"]
        if breach:
            fired.append({**rule, "value": value, "at": now})
    return fired


def notify(alert: dict, timeout: float = 5.0) -> bool:
    """POST a Slack/Discord-compatible JSON body to the rule's webhook."""
    if not alert.get("webhook_url"):
        return False
    text = (f"[SCF Analytics] {alert['project_id']}: {alert['metric']} = {alert['value']} "
            f"(threshold {alert['threshold']}, last {alert['window_min']} min)")
    body = json.dumps({"text": text, "content": text}).encode()
    req = urllib.request.Request(alert["webhook_url"], data=body,
                                 headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return 200 <= r.status < 300
    except OSError:
        return False
