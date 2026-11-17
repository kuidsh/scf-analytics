# SCF Analytics

[![tests](https://github.com/kuidsh/scf-analytics/actions/workflows/tests.yml/badge.svg)](https://github.com/kuidsh/scf-analytics/actions/workflows/tests.yml)
![licence](https://img.shields.io/badge/licence-Apache--2.0-blue)
![python](https://img.shields.io/badge/python-3.11%20%7C%203.12-informational)
![status](https://img.shields.io/badge/status-prototype%20(not%20deployed)-orange)

**Privacy-first web and API analytics for Stellar ecosystem projects, run as one shared, multi-tenant service by the Stellar Community Fund (SCF).**

This repository is a working prototype and draft proposal for the SCF RFP Track request
*"Web and API Analytics for Stellar Ecosystem Projects"*
([handbook](https://stellar.gitbook.io/scf-handbook/scf-awards/build-award/rfp-track#current-open-rfps)).

> **Status: prototype, not deployed.** 17 automated tests pass. Nothing runs in the cloud, no money is spent, and the repository touches no mainnet, wallets or keys. All numbers in the demo dashboard are generated example data. The honest, requirement-by-requirement status is in [docs/RFP-COVERAGE.md](docs/RFP-COVERAGE.md).

## Contents

[What it does](#what-it-does) · [Architecture](#architecture) · [Request lifecycle](#request-lifecycle) · [Data and privacy](#data-and-privacy) · [Metrics](#metrics) · [API reference](#api-reference) · [Quick start](#quick-start) · [RFP coverage](#rfp-coverage) · [Delivery stages](#delivery-stages) · [Roadmap](#roadmap) · [Repository layout](#repository-layout) · [Licence](#licence)

## What it does

| For | You get |
|---|---|
| **A Stellar project** | A private dashboard: how many API requests, how many failed, how fast, per route and per Stellar protocol (SEP-10, SEP-12, SEP-24, SEP-31, Soroban RPC, Horizon); a reliability target (SLO) with an error budget; website visitors from Umami; alerts to Slack or Discord; CSV export. |
| **SCF operators** | One ecosystem-wide view (per-project totals only, no route detail); self-service enrollment for projects; remove a project and erase its data; rotate or revoke any project's key. |
| **Everyone** | No cookies, no IP addresses, no user agents, no query strings, no wallet addresses in stored paths. Open source, Apache-2.0. |

Two data sources, one place:

- **Web analytics**: self-hosted [Umami](https://github.com/umami-software/umami) (MIT, used unmodified) on PostgreSQL. Page views, unique visitors, referrers, session duration, bounce rate, country, device and browser.
- **API analytics** (this repo): a project points its OpenTelemetry exporter at `POST /v1/traces`. Server spans become request volume, status-code classes and p50/p95/p99 latency per normalized route.

## Architecture

```mermaid
flowchart LR
    subgraph T["A Stellar project (tenant)"]
        SITE["Website<br/>+ Umami script"]
        API["Backend API<br/>+ OpenTelemetry SDK"]
    end

    subgraph P["SCF Analytics platform"]
        direction TB
        UM["Umami<br/>(web analytics)"]
        ING["scfa API<br/>/v1/traces, /v1/metrics,<br/>/v1/global, /v1/enroll, /v1/admin"]
        PG[("PostgreSQL<br/>requests (30 d)<br/>rollups (24 months)<br/>projects, rules")]
        AL["Alert job<br/>every 5 min"]
    end

    SITE -- "page views (no cookies)" --> UM
    API -- "OTLP/HTTP JSON<br/>x-scfa-key" --> ING
    ING --> PG
    UM --> PG
    AL --> PG
    AL -- "Slack / Discord webhook" --> HOOK(["Project's channel"])
    ING -- "tenant dashboard" --> DASH["Project dashboard"]
    ING -- "SCF-wide view<br/>(admin token)" --> OPS["SCF operators"]
    UM -. "REST client scfa/umami.py" .-> ING
```

The same Python handler runs as a local server, in Docker, or as an AWS Lambda behind an HTTP API (`infra/template.yaml`). PostgreSQL is used in production, SQLite in tests.

## Request lifecycle

```mermaid
sequenceDiagram
    autonumber
    participant S as Project service
    participant A as scfa API
    participant O as otlp.py
    participant D as Database
    participant J as Alert job
    S->>A: POST /v1/traces (OTLP JSON, x-scfa-key)
    A->>D: look up key by SHA-256 hash
    A->>O: parse spans
    O-->>A: SERVER spans only, query string removed,<br/>ids and wallet addresses replaced in the path
    A->>D: insert flat rows (30 days)
    A->>D: upsert hourly rollups (24 months)
    A-->>S: 200 accepted
    loop every 5 minutes
        J->>D: evaluate each project's rules
        J-->>S: webhook if a threshold is crossed
        J->>D: purge expired rows
    end
```

## Data and privacy

```mermaid
flowchart TD
    IN["Incoming span"] --> K{"Kind = SERVER?"}
    K -- no --> X1["Dropped"]
    K -- yes --> N["Normalize path<br/>drop query string<br/>/accounts/G…56 chars → /accounts/{account}"]
    N --> R["api_requests<br/>project, route, method, status,<br/>latency, timestamp<br/><b>kept 30 days</b>"]
    N --> U["api_rollups<br/>hourly counts + latency histogram<br/>no trace id, no span id<br/><b>kept 24 months</b>"]
```

| Stored | Never stored |
|---|---|
| project id, normalized route, method, status code, latency, timestamp | IP addresses, user agents, query strings, request or response bodies, headers, user or wallet identifiers, trace ids, span ids |
| project keys as SHA-256 hashes only | project keys in clear text (shown once at creation) |

Every database query is filtered by `project_id` (tenant isolation). Erasing a project is one operator call that deletes its rows, rollups and rules. See [docs/PRIVACY-GDPR.md](docs/PRIVACY-GDPR.md) (not legal advice).

## Metrics

| Metric | Definition |
|---|---|
| Failed rate | requests with status 500-599 ÷ all requests |
| p50 / p95 / p99 | nearest-rank percentile of latency. From the hourly rollups (windows over 30 days) it is the latency bucket's upper edge: accurate to the bucket, shown as `≈` in the dashboard |
| Protocol group | route prefix `/sep10`, `/sep12`, `/sep24`, `/sep31`, `/rpc` (Soroban RPC), `/horizon`, otherwise "Other" |
| SLO | default objective 99.5% of requests are not 5xx. **Error budget used** = failed rate ÷ (1 − target); above 100% the target is missed |
| Time ranges | 1 h, 6 h, 12 h, 1 d, 7 d, 30 d, 1 y (`?hours=1…8760`). Up to 30 days: exact raw rows. Beyond: hourly rollups |
| Alert rules | `error_rate`, `p95_ms`, `p99_ms`, and `requests_min` (fires when traffic drops below a threshold, which catches silent outages) |

## API reference

| Method and path | Auth header | Purpose |
|---|---|---|
| `POST /v1/traces` | `x-scfa-key` | Ingest OTLP/HTTP **JSON** traces (protobuf returns 415; bodies over 5 MB return 413) |
| `GET /v1/metrics?hours=24[&format=csv]` | `x-scfa-key` | The project's own metrics (JSON) or per-route CSV |
| `GET /v1/global?hours=24` | `x-scfa-admin` | SCF-wide view: per-project totals only |
| `POST /v1/enroll` | none | Self-service sign-up `{"id","name"}`; returns the key once. `ENROLLMENT=closed` disables it |
| `GET /v1/admin/projects` | `x-scfa-admin` | List projects |
| `POST /v1/admin/projects/<id>/rotate-key` | `x-scfa-admin` | New key; the old one stops working at once |
| `POST /v1/admin/projects/<id>/revoke-key` | `x-scfa-admin` | Key stops working, none issued |
| `DELETE /v1/admin/projects/<id>` | `x-scfa-admin` | Remove the project and erase all its data |
| `GET /healthz` | none | Liveness |

Point any OpenTelemetry SDK at it:

```bash
export OTEL_EXPORTER_OTLP_TRACES_ENDPOINT=http://localhost:8080/v1/traces
export OTEL_EXPORTER_OTLP_PROTOCOL=http/json
export OTEL_EXPORTER_OTLP_HEADERS=x-scfa-key=<project key>
```

## Quick start

Python 3.11+ only. There is no Node, npm or build step.

```bash
python -m pytest -q                  # 17 tests, offline, SQLite
python demo/build_demo.py            # writes demo/data.json (about 1.5 minutes)
python -m http.server 8000           # open http://localhost:8000/demo/
```

The demo page shows four made-up projects with traffic generated through the real pipeline: time ranges up to a year, website visitors, SLO bars, protocol breakdown, CSV download, the RFP coverage table, and the architecture and tests behind every number.

Run the API with a file database so project keys persist between shells (the default `:memory:` database cannot be shared):

```bash
export DATABASE_URL=local.sqlite ADMIN_TOKEN=dev
python -m scfa.app                                   # http://localhost:8080
curl -X POST localhost:8080/v1/enroll -d '{"id":"my-anchor","name":"My Anchor"}'   # prints the key once
curl "localhost:8080/v1/metrics?hours=6" -H "x-scfa-key: <KEY>"
curl localhost:8080/v1/global -H "x-scfa-admin: dev"
```

Full stack with PostgreSQL and Umami (needs Docker; runs locally):

```bash
cd infra
PG_PASSWORD=localdev UMAMI_SECRET=localdev ADMIN_TOKEN=dev docker compose -p scfa-local up -d --build
# API on :8080, Umami on :3000 (login admin / umami). Stop and wipe: docker compose -p scfa-local down -v
```

## RFP coverage

Summary (full table with evidence in [docs/RFP-COVERAGE.md](docs/RFP-COVERAGE.md); the requirements are paraphrased from the handbook, so re-read the source before relying on this):

| Status | Requirements |
|---|---|
| **Built and tested** | tenant isolation and SCF global view · self-service enrollment · remove a project · key generation, rotation and revocation · OpenTelemetry ingest into PostgreSQL · path normalization · 24-month aggregates · web-metrics client · OSI licence |
| **Designed, not built** | Umami vs GoatCounter rationale ([docs/WEB-ANALYTICS.md](docs/WEB-ANALYTICS.md)) · web hardening: pinned scripts, supply-chain defences, bot mitigation, ad-blocker-resistant naming · GDPR, residency, erasure ([docs/PRIVACY-GDPR.md](docs/PRIVACY-GDPR.md)) · 99.99% ingestion and 99.90% dashboard availability, 24-hour patching, handover ([docs/OPERATIONS.md](docs/OPERATIONS.md)) |
| **Open** | live run against a real Umami · load test at the 1,000,000 requests/day design target · runbook and onboarding guide · proof of adoption (3 projects on web analytics, 1 on API, demo videos) · applicant track record with SCF/SDF |

## Delivery stages

How the platform reaches the RFP's scope, stage by stage. Each stage says what is built technically and what users can do once it is done. The full draft submission is in [PROPOSAL.md](PROPOSAL.md).

| Stage | Technical result | What users get |
|---|---|---|
| **T0 · Foundation** (month 1) | Public repository, architecture, privacy and operations documents, the Umami vs GoatCounter rationale, staging environment, first tagged release with a bill of materials | Anyone can read, run and review the design and the code |
| **T1 · MVP** (month 2.5) | Multi-tenant Umami (one website per project), per-project dashboard served by the API, hardened tracker script with an integrity hash, backup and restore drill | A Stellar project signs up, adds one script and one exporter setting, and sees its own web and API data |
| **T2 · Pilots and scale** (month 4) | 3 SCF-funded projects on web analytics and 1 on API traffic live, SCF global view and alert rules, onboarding guides for the JavaScript, Go, Rust and Python SDKs, a load test at 1,000,000 requests a day | SCF operators see the whole ecosystem; projects get Slack or Discord alerts and instrument their service from a guide |
| **T3 · Launch** (month 5) | Production with TLS, backups and a redundant ingestion path, failover test and measured availability report, runbook, tested handover | A reliable public service run by the proposer for 12 months, then handed to a community operator |

Possible later features, not in the committed scope: public status page, anomaly alerts, per-project SLO targets, SEP-aware views (for example the SEP-24 deposit flow), Soroban RPC method breakdown, protobuf OTLP, email digests, Prometheus export. See section 3.2 of [PROPOSAL.md](PROPOSAL.md).

## Roadmap

```mermaid
flowchart LR
    A["v0.1 prototype<br/>ingest, rollups, metrics,<br/>alerts, enrollment, demo"] --> B["v0.2<br/>live Umami run,<br/>per-project Umami provisioning,<br/>dashboard served by the API"]
    B --> C["v0.3<br/>onboarding guides,<br/>protobuf OTLP,<br/>web hardening"]
    C --> D["v1.0<br/>load test, redundant hosting,<br/>runbook, pilots, handover plan"]
```

## Repository layout

```
scfa/otlp.py       OTLP JSON -> request records; path normalization
scfa/store.py      PostgreSQL / SQLite storage, hashed keys, retention, operator controls
scfa/rollup.py     hourly aggregates (counts + latency histograms), 24 months
scfa/metrics.py    volume, status classes, percentiles, protocol groups, SLO, global view
scfa/alerts.py     rule evaluation + Slack/Discord webhook
scfa/umami.py      Umami REST client + web_summary()
scfa/app.py        HTTP API: Lambda handler + local dev server
demo/              build_demo.py (example traffic through the real pipeline), index.html, data.json
docs/              RFP-COVERAGE, WEB-ANALYTICS, PRIVACY-GDPR, OPERATIONS
infra/             AWS SAM template (not deployed), docker-compose (Postgres + Umami + API), initdb
tests/test_core.py 17 tests: SQLite, offline
PROPOSAL.md        draft SCF submission
```

Design rules: core code is Python standard library only (the single production dependency is `psycopg`); every behaviour change has a test; tests run offline.

## Licence

Apache-2.0 (see [LICENSE](LICENSE)). Umami, deployed alongside and unmodified, is MIT.
