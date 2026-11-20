# Status

A dated public log of what has landed in SCF Analytics, newest first. Each entry says what was built or changed and how it can be checked. "Built" means code plus a passing automated test; anything checked by hand says so.

After an award, this file carries the monthly status update promised in [PROPOSAL.md](PROPOSAL.md) section 6 (progress against the tranche, availability, incidents, security fixes, enrolled projects, support response times), mirrored in the SCF Discord.

## 2026-11-19

- **Submitting to SCF #46, RFP Track** ("Web and API Analytics for Stellar Ecosystem Projects"). The full proposal is [PROPOSAL.md](PROPOSAL.md).
- **Proposal aligned with the SCF handbook** (Submission Criteria, RFP Track, Budget & Deliverable Guidelines): tranche #0 on acceptance with no deliverables, then #1 MVP (month 1.5), #2 pilots and scale (month 3, testnet equivalent) and #3 production launch (month 5, mainnet equivalent); a cost and a verification method for every deliverable; a stated decentralization rationale; the security review moved out of the request, because audits are ineligible costs. Commits `25e340f`, `da4f8fe`.
- **Technical architecture document** added and checked against the code, with every part marked Built, Designed or Open: [docs/TECHNICAL-ARCHITECTURE.md](docs/TECHNICAL-ARCHITECTURE.md). Commit `1509d2f`.
- **Threat model draft** published: [docs/THREAT-MODEL.md](docs/THREAT-MODEL.md). It lists what is in place today, with the test that proves each item, and what is still open. Tranche #2 completes it with a monitoring plan.
- **This status log** started.

## 2026-11-17

- **Enrollment closed by default.** A public deployment cannot be used by strangers to create tenants: operators always can; `ENROLLMENT=invite` needs an invite code; `open` lets anyone in; both invite and open are capped at 10 new projects an hour (HTTP 429 after that). Test: `test_enrollment_is_closed_by_default_and_gated`. Commit `d8f3d67`.
- **Availability and cost documents aligned.** The RFP's 99.99% ingestion and 99.90% dashboard targets are measured and published, never guaranteed. The redundant deployment is priced at about US$131 a month ([COSTS.md](COSTS.md), [docs/OPERATIONS.md](docs/OPERATIONS.md)). One load-test target everywhere: 1,000,000 requests a day. Commits `63a0118`, `d8f3d67`.
- **RFP gaps closed in code**, each with a test: path normalization (wallet addresses, hashes, ids, UUIDs and long tokens become placeholders), hourly rollups kept 24 months for month and year views, self-service enrollment, operator key rotation and revocation, project deletion (erasure), and an Umami client that returns every web metric the RFP names. Documents for Umami vs GoatCounter, web hardening, GDPR and erasure, and operations. Requirement-by-requirement status: [docs/RFP-COVERAGE.md](docs/RFP-COVERAGE.md). Commit `8faf550`.
- **Demo page redesigned** ([demo/index.html](demo/index.html)): four example projects, 1-hour to 1-year views, an SLO card, web visitors, the RFP coverage table. All demo data is example data, generated through the real ingest path by `demo/build_demo.py`.
- **Checked by hand on a local Docker stack** (PostgreSQL + Umami + the API, `infra/docker-compose.yml`): enroll a project, ingest traces with path normalization, read the year view from rollups, delete the project. Not yet part of CI. Fixed along the way: Umami failed to start because its database did not exist (`infra/initdb/01-umami.sql`).
- **Prototype v0.1 published**: OpenTelemetry (OTLP/HTTP JSON) ingest, per-project keys stored only as SHA-256 hashes, tenant-isolated metrics (volume, failed rate, p50/p95/p99 per route), Stellar protocol grouping (SEP-10, SEP-12, SEP-24, SEP-31, Soroban RPC, Horizon; the group is renamed Stellar RPC in tranche #1), SLO with an error budget, Slack and Discord alert webhooks, CSV export, the SCF global view, and an AWS SAM template. Standard-library Python plus `psycopg`. 18 automated tests pass offline (`python -m pytest -q`). Commit `b3536b4`.

## Not done yet

The open items are tracked in [docs/RFP-COVERAGE.md](docs/RFP-COVERAGE.md). The largest: nothing is deployed; Umami has not been run live through the client; web hardening, the load test, redundant hosting, the runbook, onboarding guides and the monitoring plan are not built; no pilot project is enrolled yet.
