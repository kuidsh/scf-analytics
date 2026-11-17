# DRAFT — SCF RFP Track submission

**RFP:** Web and API Analytics for Stellar Ecosystem Projects
**Applicant:** David Vega (individual, Mexico)
**Requested:** US$64,000 in XLM · **Duration:** 4 months build + 12 months hosting

> Draft for David to edit. Figures marked (est.) are planning estimates.

## Summary

A shared analytics service SCF runs for its funded projects. Web analytics on
self-hosted Umami; API analytics from OpenTelemetry traces into PostgreSQL;
a private dashboard per project and a global view for SCF; a monitoring and
alerting baseline. One open-source monorepo, hosted for 12 months, with
stewardship handed to a community operator between months 6 and 12.

## Why this team

13+ years in software and data engineering (Python, SQL, AWS, ETL pipelines,
REST APIs). Two production Python + blockchain systems, including an
election-day integrity system with on-chain verification and auditable logs.
A working prototype already exists: OTLP ingest, tenant isolation, percentile
metrics, alert rules, 11 passing tests.

## Deliverables and tranches

| Tranche | Share | Deliverable |
|---|---|---|
| 0 · Award | 10% · US$6,400 | Repo public, architecture doc, prototype running on staging |
| 1 · MVP | 20% · US$12,800 | Umami multi-tenant setup, OTLP ingest, per-project dashboard, 3 pilot SCF projects onboarded |
| 2 · Testnet | 30% · US$19,200 | SCF global view, alert rules UI, onboarding guide for JS/Go/Rust/Python OTel SDKs, load test (10M spans/day) |
| 3 · Launch | 40% · US$25,600 | Production on AWS with TLS, backups, runbook; 10+ projects onboarded; handover plan to community operator |

## Budget

| Line | USD |
|---|---|
| Engineering, 4 months (est. 560 h) | 56,000 |
| Hosting, 12 months (AWS Lightsail, see COSTS.md) | 1,200 |
| Support and on-call, months 1–12 (est.) | 5,400 |
| Security review of auth and data isolation (est.) | 1,400 |
| **Total** | **64,000** |

## Privacy

No IP addresses, user agents or query strings are stored. Raw API rows are
purged after 30 days; only aggregates are kept. Each project sees only its own
data; SCF's global view shows per-project totals, never route detail.

## KPIs

Projects onboarded, weekly active dashboards, ingest uptime (target 99.5%),
p95 ingest latency, number of alert rules in use.
