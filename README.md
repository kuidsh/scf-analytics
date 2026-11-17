# SCF Analytics — prototype

![tests](../../actions/workflows/tests.yml/badge.svg)

Prototype for the Stellar Community Fund (SCF) RFP **"Web and API Analytics for
Stellar Ecosystem Projects"**: a shared, multi-tenant, privacy-first analytics
service that SCF runs for funded projects.

* **Web analytics**: self-hosted [Umami](https://github.com/umami-software/umami) (MIT, PostgreSQL), as the RFP requires.
* **API analytics** (this repo): projects point their OpenTelemetry exporter at
  `/v1/traces`; server spans become request volume, status-code classes and
  p50/p95/p99 latency per route, stored in PostgreSQL.
* **Views**: each project reads its own metrics with its key; SCF reads an
  ecosystem-wide view with an admin token.
* **Monitoring baseline**: per-project threshold rules (error rate, p95, p99,
  traffic drop) checked every 5 minutes; alerts go to a Slack/Discord webhook.
* **Privacy**: no IPs, user agents or query strings stored; raw rows purged after 30 days.

Status: **prototype, not deployed**. No mainnet, no wallets, no keys.

## Layout

```
scfa/otlp.py      OTLP/HTTP JSON -> API request records (semconv old + new names)
scfa/store.py     PostgreSQL / SQLite storage, hashed project keys, retention
scfa/metrics.py   volume, status classes, nearest-rank percentiles, global view
scfa/alerts.py    rule evaluation + webhook notify
scfa/umami.py     Umami REST client (login + website stats)
scfa/app.py       HTTP API: Lambda handler + local dev server
infra/template.yaml       AWS SAM (Lambda + HTTP API + 5-min schedule), optional
infra/docker-compose.yml  Lightsail single-box deployment (Umami + API + Postgres)
demo/build_demo.py        example traffic through the real pipeline -> demo/data.json
tests/test_core.py        pytest suite (11 tests, SQLite, no network)
PROPOSAL.md       draft SCF RFP-track submission (milestones by tranche, budget)
COSTS.md          AWS cost model with sources
```

## Run locally

```bash
python3 -m pytest -q                 # 11 passed
python3 demo/build_demo.py           # writes demo/data.json
ADMIN_TOKEN=dev python3 -m scfa.app  # API on :8080 (SQLite in memory)
```

See the example dashboards (made-up projects, real pipeline):

```bash
python3 -m http.server 8000         # then open http://localhost:8000/demo/
```

Point any OpenTelemetry SDK at it:

```bash
export OTEL_EXPORTER_OTLP_TRACES_ENDPOINT=http://localhost:8080/v1/traces
export OTEL_EXPORTER_OTLP_PROTOCOL=http/json
export OTEL_EXPORTER_OTLP_HEADERS=x-scfa-key=<project key>
```

Create a project key in a Python shell: `Store(url).create_project("my-anchor", "My Anchor")`.

## Deploy (only after an award; costs money)

1. Lightsail: create a 4 GB Linux instance and a standard managed PostgreSQL database.
2. On the instance: install Docker, clone this repo, set `PG_PASSWORD`,
   `UMAMI_SECRET`, `ADMIN_TOKEN`, then `docker compose -f infra/docker-compose.yml up -d`.
3. Put TLS in front (Lightsail load balancer or Caddy) and point DNS at it.
4. Optional serverless ingest: `sam build -t infra/template.yaml && sam deploy --guided`.

## Licence

Apache-2.0 (see `LICENSE`). Umami, deployed alongside, is MIT.
