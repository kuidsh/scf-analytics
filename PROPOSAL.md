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
A working prototype already exists: OTLP ingest with path normalization, tenant
isolation, self-service enrollment, key rotation and revocation, 24-month hourly
rollups, percentile metrics, SLO view, alert rules, an Umami web-metrics client,
and 17 passing tests.

> TODO (David): the RFP weights relevant open-source and SCF/SDF track record
> heavily and excludes builders unknown to SCF. Add concrete links here
> (past SCF rounds, SDF programmes, Stellar repos, community roles), or find
> a co-applicant who has them. Nothing in this repo can supply this.

## Deliverables and tranches

| Tranche | Share | Deliverable |
|---|---|---|
| 0 · Award | 10% · US$6,400 | Repo public, architecture doc, Umami vs GoatCounter rationale, privacy/GDPR doc, prototype running on staging |
| 1 · MVP | 20% · US$12,800 | Umami multi-tenant setup (one website per project), OTLP ingest, per-project dashboard with web and API metrics, **at least 3 SCF-funded projects on web analytics and 1 on API traffic, with demo videos** |
| 2 · Testnet | 30% · US$19,200 | SCF global view, alert rules UI, onboarding guide for JS/Go/Rust/Python OTel SDKs, load test (10M spans/day) |
| 3 · Launch | 40% · US$25,600 | Production on AWS with TLS, backups and a redundant ingestion path (see docs/OPERATIONS.md), runbook; 10+ projects onboarded; handover plan to community operator |

## Budget

| Line | USD |
|---|---|
| Engineering, 4 months (est. 560 h) | 56,000 |
| Hosting, 12 months (AWS Lightsail, see COSTS.md) | 1,200 (**single-box estimate; the redundant deployment needed for the RFP's 99.99% ingestion target must be re-priced before submitting**) |
| Support and on-call, months 1–12 (est.) | 5,400 |
| Security review of auth and data isolation (est.) | 1,400 |
| **Total** | **64,000** |

## Privacy

No IP addresses, user agents or query strings are stored, and identifiers inside
paths (wallet addresses, hashes, ids) are replaced by placeholders before storage.
Flat request rows are purged after 30 days; hourly aggregates (counts and latency
histograms, no trace or span ids) are kept 24 months. Each project sees only its
own data; SCF's global view shows per-project totals, never route detail. Tenant
erasure is one operator call. See docs/PRIVACY-GDPR.md.

## RFP coverage

Requirement-by-requirement status (built, designed or open) is in
docs/RFP-COVERAGE.md. Web-analytics hardening and the Umami choice are in
docs/WEB-ANALYTICS.md; availability, patching and handover are in
docs/OPERATIONS.md.

## KPIs

Projects onboarded, weekly active dashboards, ingestion availability (RFP target
99.99%), dashboard availability (RFP target 99.90%), critical/high vulnerabilities
patched within 24 hours, p95 ingest latency, number of alert rules in use.
