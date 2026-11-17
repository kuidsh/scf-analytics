"""Turn OTLP/HTTP JSON trace payloads into flat API-request records.

Only SERVER spans (kind 2) are counted: each one is a request a project's API
answered. Attribute names follow the OpenTelemetry HTTP semantic conventions,
with the older (pre-1.20) names accepted as fallbacks.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

SPAN_KIND_SERVER = 2

ROUTE_KEYS = ("http.route", "url.path", "http.target")
METHOD_KEYS = ("http.request.method", "http.method")
STATUS_KEYS = ("http.response.status_code", "http.status_code")


# Path normalization (hard-coded default rule set). Replaces identifiers inside a route with
# placeholders, so wallet addresses, hashes and ids are never stored and the number of
# distinct routes stays small. Applied before anything is written.
_STRKEY = re.compile(r"^[GCMSTPX][A-Z2-7]{55,68}$")
_HEX = re.compile(r"^(?:0x)?[0-9a-fA-F]{32,}$")
_UUID = re.compile(r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$")
_NUM = re.compile(r"^\d+$")
_OPAQUE = re.compile(r"^(?=.*\d)(?=.*[A-Za-z])[A-Za-z0-9_\-=.%+]{24,}$")
MAX_ROUTE_LEN = 200


def _norm_segment(seg: str) -> str:
    if not seg or seg[0] in "{:" or seg.startswith("<"):
        return seg  # already a route template such as /accounts/{id}
    if _STRKEY.match(seg):
        return {"G": "{account}", "M": "{account}", "C": "{contract}"}.get(seg[0], "{key}")
    if _UUID.match(seg):
        return "{uuid}"
    if _HEX.match(seg):
        return "{hash}"
    if _NUM.match(seg):
        return "{id}"
    if _OPAQUE.match(seg):
        return "{token}"
    return seg


def normalize_path(route: str) -> str:
    route = (route or "/").split("?", 1)[0].split("#", 1)[0]
    out = "/".join(_norm_segment(s) for s in route.split("/"))
    return (out if out.startswith("/") else "/" + out)[:MAX_ROUTE_LEN]


@dataclass(frozen=True)
class ApiRequest:
    service: str
    route: str
    method: str
    status: int
    duration_ms: float
    ts_unix: int  # request start, whole seconds


def _attr_value(v: dict):
    for k in ("stringValue", "intValue", "doubleValue", "boolValue"):
        if k in v:
            return v[k]
    return None


def _attrs(items) -> dict:
    return {a["key"]: _attr_value(a.get("value", {})) for a in items or []}


def _first(d: dict, keys, default=None):
    for k in keys:
        if d.get(k) is not None:
            return d[k]
    return default


def _kind(span) -> int:
    kind = span.get("kind", 0)
    if isinstance(kind, str):  # some exporters send the enum name
        return SPAN_KIND_SERVER if kind.endswith("SERVER") else 0
    return int(kind)


def parse_traces(payload: dict) -> list[ApiRequest]:
    out: list[ApiRequest] = []
    for rs in payload.get("resourceSpans", []):
        res = _attrs(rs.get("resource", {}).get("attributes"))
        service = str(res.get("service.name", "unknown"))
        for ss in rs.get("scopeSpans", []):
            for span in ss.get("spans", []):
                if _kind(span) != SPAN_KIND_SERVER:
                    continue
                a = _attrs(span.get("attributes"))
                start = int(span["startTimeUnixNano"])
                end = int(span["endTimeUnixNano"])
                route = str(_first(a, ROUTE_KEYS, span.get("name", "/")))
                route = normalize_path(route)  # no query strings, no ids or wallet addresses
                out.append(
                    ApiRequest(
                        service=service,
                        route=route,
                        method=str(_first(a, METHOD_KEYS, "GET")).upper(),
                        status=int(_first(a, STATUS_KEYS, 0)),
                        duration_ms=max(0.0, (end - start) / 1e6),
                        ts_unix=start // 1_000_000_000,
                    )
                )
    return out
