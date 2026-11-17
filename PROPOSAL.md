# DRAFT: SCF RFP Track submission

**RFP:** Web and API Analytics for Stellar Ecosystem Projects
**Applicant:** David Vega (individual, Mexico)
**Request:** US$57,400 in XLM, for development only (our estimate; the RFP states no budget)
**Plan:** 5 months to build and launch, then 12 months of hosting and support that the applicant funds

> Working draft for David to edit. Items under "Open decisions" must be resolved or removed before submitting. Figures marked (est.) are planning estimates, not quotes. Handbook facts below were read on 2026-11-17 from the SCF Handbook; re-check them before submitting.

## 1. Summary

A shared analytics service that SCF runs for the projects it funds. Each project gets a private dashboard that combines **website visitors** (self-hosted Umami) and **API health** (OpenTelemetry traces turned into request volume, errors and latency). SCF operators get one ecosystem-wide view. Everything is open source in one monorepo, privacy-first (no cookies, no IP addresses, no wallet addresses in stored data), and hosted by us for 12 months before handover to a community operator.

## 2. Where we are today

A working prototype exists and is public. Facts, not promises:

| Built and tested (17 automated tests) | Not built yet |
|---|---|
| OpenTelemetry ingest (JSON), path normalization, per-project keys stored as hashes | Live run against a real Umami; one Umami website per project |
| Hourly aggregates kept 24 months; exact rows kept 30 days | Web-script hardening (pinned scripts with integrity hashes, bot filtering) |
| Self-service enrollment; operator remove, key rotate and revoke, full erasure | Dashboard served live by the API (the demo page is static) |
| Stellar protocol grouping, SLO and error budget, alert rules to Slack/Discord, CSV export | Onboarding guides, runbook, load test, redundant hosting |
| Umami client covering every RFP web metric | Pilot projects, demo videos |

Requirement-by-requirement status: [docs/RFP-COVERAGE.md](docs/RFP-COVERAGE.md). Prior work is presented as exactly that; the award funds what is in the right-hand column.

## 3. Scope

### 3.1 Committed scope (what the tranches pay for)

1. **Web analytics.** Umami, unmodified and pinned by version, one website per project, tracker script served from our domain at a versioned path with a Subresource Integrity hash. Metrics: page views, unique visitors, referrers, session duration, bounce rate, country, device, browser.
2. **API analytics.** Projects dual-export OpenTelemetry to us. We keep only standardized metrics (counts and latency histograms); traces, spans and logs are discarded. Routes are normalized so wallet addresses and ids never reach the database.
3. **Per-project dashboard** (web and API together), **SCF global view**, **alert rules** with Slack/Discord webhooks, **CSV export**.
4. **Operations for SCF:** self-service enrollment, remove a non-ecosystem project, issue, rotate and revoke keys.
5. **Privacy and security:** documented GDPR position, data residency in a named region, erasure workflow, pinned images and dependencies, software bill of materials, signed releases.
6. **Hosting, support, handover:** 12 months of operation, measured availability reporting, runbook, tested handover.

### 3.2 Possible features (not promised; added only if time and pilot feedback justify them)

| Feature | Why it could matter | Rough effort (est.) |
|---|---|---|
| Public status page per project | Projects show uptime to their own users | 1 week |
| Anomaly alerts (sudden 5xx jump, traffic drop vs the same hour last week) | Fewer threshold tweaks | 1-2 weeks |
| Per-project SLO targets | Today the objective is fixed at 99.5% | 3 days |
| SEP-aware views (for example the SEP-24 deposit flow step by step) | Stellar-specific insight no generic tool gives | 2 weeks |
| Soroban RPC method breakdown | See which contract calls are slow | 1 week |
| OTLP over protobuf | Today only JSON is accepted | 1-2 weeks |
| Email alerts and a weekly digest | Reach teams not using Slack or Discord | 1 week |
| Prometheus-compatible export | Lets teams reuse Grafana | 1 week |
| Opt-in public ecosystem leaderboard | Ecosystem-wide adoption signal | 1 week plus policy decision |
| GoatCounter adapter | An alternative web engine behind the same dashboard | 2 weeks |

## 4. Timeline and tranches

Milestones are chosen so that anyone outside the team can verify them: a public URL, a tagged release, a committed report, or a signed letter. Pilot outreach starts in **month 0**, before the award, because pilots depend on other people's calendars.

| Stage | Target | Share | Amount | Verifiable deliverables |
|---|---|---|---|---|
| **T0 · Foundation** | month 1 | 10% | US$5,740 | Public repository; architecture, privacy and operations documents; the Umami vs GoatCounter rationale; staging environment running the current prototype; first tagged release with a bill of materials; at least 2 letters of interest from SCF-funded projects |
| **T1 · MVP** | month 2.5 | 20% | US$11,480 | Umami multi-tenant on staging, one website per project; per-project dashboard (web and API) served by the API; hardened tracker script with integrity hash; backup and restore drill report; first web pilot live |
| **T2 · Pilots and scale** | month 4 | 30% | US$17,220 | **3 SCF-funded projects on web analytics and 1 on API traffic, live**, with demo videos; SCF global view and alert rules in the product; onboarding guides for the JavaScript, Go, Rust and Python OpenTelemetry SDKs; load test at 1,000,000 requests a day (the RFP design target) with a published report; continuous vulnerability scanning in CI |
| **T3 · Launch** | month 5 | 40% | US$22,960 | Production environment with TLS, backups and a redundant ingestion path; failover test and a measured availability report; runbook; 10 or more projects enrolled; handover plan with a tested data migration to a second environment |
| **Operation** | months 6-17 | funded by the applicant | not requested | 12 months of hosting and support after T3; monthly availability and security report; handover to a community operator between months 6 and 12 of operation, at SCF's discretion |

**Tranche structure.** The SCF Handbook says awards are paid in milestone-based tranches, each with its own deliverables, but does not give a number of tranches or percentages (its "Tranches & Deliverables" page holds the detail). The 10/20/30/40 split is therefore **our proposal**, not an SCF rule. If SCF uses a different structure, T0 merges into T1 and the stages keep their deliverables. The handbook also requires each later tranche to be submitted within 90 days of the previous payment; the gaps above are 45 to 75 days, and SCF is told in advance if a date will slip, because a missed deadline without notice forfeits the remaining funds.

**Why 5 months and not 4.** The handbook says awards are meant to cover roughly 4 months of development and that projects typically run 3 to 6 months. We plan 5, within that range, because pilot onboarding and a load test depend on third parties and on infrastructure that cannot be rushed, so the pilots sit in T2 where they can be demonstrated. Dropping the stretch work in T2 would return the plan to 4 months.

## 5. Engineering effort (est.)

| Stage | Hours (est.) | Main work |
|---|---|---|
| T0 | 60 | documents, public release, staging, pilot outreach |
| T1 | 150 | Umami provisioning, API-served dashboard, tracker hardening, backup drill |
| T2 | 190 | pilots, onboarding guides, load test, scanning in CI |
| T3 | 160 | redundant ingestion, failover test, runbook, handover rehearsal |
| **Total** | **560** | about 28 hours a week over 5 months |

## 6. Service levels: what we commit to, and how we prove it

| RFP target | Our commitment |
|---|---|
| 99.99% ingestion | Designed for it: stateless ingestion on two servers in different availability zones behind a load balancer, exporters retry so short outages lose nothing. We **measure and publish** availability monthly and say plainly if the target is missed. T3 includes a failover test and a measured availability report; we do not claim a guarantee that one provider cannot give |
| 99.90% dashboards | Separate, simpler deployment with its own checks |
| Critical and high vulnerabilities patched in 24 hours | One production dependency, pinned images, daily dependency scanning, same-day release process. A single operator in one time zone cannot give round-the-clock cover, so a **named backup operator** is appointed by month 3 and the response hours are published |
| 12 months of hosting and support | Included after T3 |
| Handover in months 6-12 | Repository, infrastructure code, domain, data export and runbook; counted as complete only when the new operator runs the system alone for one week |

Details: [docs/OPERATIONS.md](docs/OPERATIONS.md).

## 7. Privacy, security and supply chain

- **No personal data stored.** No cookies, no IP addresses, no user agents, no query strings; wallet addresses, hashes and ids in paths are replaced by placeholders before storage. Details and the erasure workflow: [docs/PRIVACY-GDPR.md](docs/PRIVACY-GDPR.md). This is not a legal opinion; we will obtain one before launch.
- **Data residency:** all tenant data stays in one EU region, stated publicly. Proposed: AWS Frankfurt (Germany). Before the award we confirm that Lightsail offers the managed high-availability database and load balancer there; if not, the nearest EU region that does is used.
- **Tenant isolation:** every query filtered by project; the global view shows per-project totals only; covered by automated tests.
- **Supply chain:** Umami pinned by version and image digest, unmodified; new releases reviewed by a person; signed releases with a bill of materials; tracker script versions are immutable.
- **Web hardening and bot mitigation:** [docs/WEB-ANALYTICS.md](docs/WEB-ANALYTICS.md). We state what it stops and what it does not (bots that run JavaScript, large botnets).

## 8. Adoption plan

- **Target:** 3 SCF-funded projects on web analytics and 1 on API traffic by T2.
- **Process:** shortlist 4 to 6 funded projects in month 0; ask for letters of interest before the award; onboard with the guide and examples. The project adds **one script tag** for web and **one extra exporter** for API (alongside its existing monitoring, which stays untouched).
- **Success criteria:** the project sees its own data within one day of starting; no personal data leaves its site; the project confirms in writing.
- **Pilot data is used** to tune the bot limits and to feed the load report.
- We list pilot names only after a letter exists.

## 9. Budget

**Requested from SCF (development, until launch)**

| Line | USD |
|---|---|
| Engineering, 5 months (est. 560 h) | 56,000 |
| Security review of authentication and data isolation (est.) | 1,400 |
| **Total request** | **57,400** |

**Funded by the applicant (12 months of operation, required by the RFP)**

| Line | USD |
|---|---|
| Hosting, redundant deployment (priced below) | about 1,600 |
| Support and on-call, 12 months (est.) | 5,400 |
| **Total** | **about 7,000** |

The SCF Handbook describes awards as covering development until launch and does not address hosting, operations or support afterwards; the RFP makes those 12 months an obligation of the proposer. We therefore **do not ask SCF to fund operation**. The applicant carries about US$7,000 across the 12 months, plus about US$12 a month for a staging server while building.

**Hosting priced (AWS Lightsail pricing page, read 2026-11-17):** two 4 GB instances in different availability zones (2 x US$24), a load balancer (US$18), a 2 GB managed PostgreSQL with the high-availability plan (US$60) and about US$5 of snapshots: about US$131 a month, about US$1,570 a year. The earlier single-server design cost about US$59 a month; the difference is what the RFP's availability target costs. Details: [COSTS.md](COSTS.md).

Excluded from the request: marketing, legal and entity fees, contingency, and the legal opinion on GDPR (to be quoted, see section 13).

## 10. Team

**David Vega, applicant (individual, Mexico).** 13+ years in software and data engineering (Python, SQL, AWS, ETL pipelines, REST APIs); two production Python and blockchain systems, including an election-day integrity system with on-chain verification and auditable logs. This repository is public evidence of delivery: a tested prototype, written requirement-by-requirement status, and documents for privacy, operations and web hardening.

**Track record, stated plainly.** The applicant has no previous SCF or SDF award. The RFP excludes builders unknown to SCF, says a weak track record may be disqualifying, and the handbook notes that SCF relies heavily on referral signals, so this is the largest risk to the application. The plan:

1. **Referral.** Ask a person or team already known to SCF who can vouch for the work to give a referral code, to be entered on the Interest form. A referral is not mandatory, but without one the application only gets the basic eligibility review.
2. **Co-applicant (optional).** If no referral is found, bring in a Stellar builder with a public SCF or SDF record as a named, KYC-verified team member with a defined role and share of delivery.
3. **Pilot letters.** Letters of interest from SCF-funded projects (stage T0) are the best independent evidence we can collect before the award.
4. **KYC.** As an individual the applicant completes KYC personally; teams complete it per contributor.

Nothing is claimed here that cannot be checked. Names for steps 1 and 2 are in "Open decisions"; the proposal is not ready to submit until step 1 or 2 has a name.

## 11. Risks and how we handle them

| Risk | Mitigation |
|---|---|
| Builder not yet known to SCF (no previous award) | Referral code or co-applicant (section 10); pilot letters; public prototype as evidence of delivery. This is the main risk |
| Other teams submitting for the same RFP | Differentiate on what is already running and tested, honest status reporting, and Stellar-specific insight (protocol grouping, SLO) |
| No pilots secured yet | Outreach from month 0; letters before award; the pilots sit in T2, not earlier |
| 99.99% ingestion on a small budget | Redundant deployment priced (about US$131 a month); availability measured, reported and not guaranteed |
| 24-hour patching with one operator | Automation, a named backup operator, published response hours |
| Operating costs may not be eligible | Not requested: the applicant funds the 12 months of operation (section 9) |
| Privacy compliance depends on law and jurisdiction | Documented position, legal review before launch, no overclaiming |
| Umami behaviour not yet verified on a live instance | First task of T1; documented fallback to the GoatCounter adapter |
| XLM price moves between award and payment | Awards are valued in USD at the payment-day price (per the handbook); convert on receipt |
| Plan is 5 months while the handbook speaks of about 4 months of development | Within the typical 3 to 6 months; stretch work in T2 can be dropped to return to 4 |

## 12. KPIs

Projects enrolled; projects live on web and on API; weekly active dashboards; ingestion availability (measured, against 99.99%); dashboard availability (against 99.90%); time to patch critical and high vulnerabilities; p95 ingest latency; alert rules in use; time for a new project to see its first data.

## 13. Open decisions (remove this section before submitting)

1. **Referral or co-applicant (blocking).** Who will give the referral code, or who joins as a co-applicant, and what is their public SCF/SDF record?
2. Confirm on the SCF Tranches & Deliverables page (or with the SCF team) the number and shares of tranches, and that the 90-day rule fits section 4.
3. Confirm Lightsail offers the high-availability database and load balancer in Frankfurt; otherwise pick the nearest EU region that does.
4. Which 4 to 6 funded projects to approach for pilots.
5. Whether to buy a legal opinion on GDPR before launch (get a quote; not included in the request).
6. Whether the applicant can fund about US$7,000 of operation plus the staging server, since operation is not requested.
7. Whether to keep 5 months or return to 4 by dropping stretch items from T2.
