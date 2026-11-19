# SCF Analytics: SCF RFP Track submission

**RFP:** Web and API Analytics for Stellar Ecosystem Projects
**Team:** b2bdev (Ecuador) and b2bdev2 (Mexico), two engineers working together at B2B, an Ecuador-based technology consultancy
**Request:** US$56,000 in XLM, for development only (our estimate; the RFP states no budget)
**Plan:** 5 months to build and launch in three milestone tranches, then 12 months of hosting and support that the applicant funds

> Figures marked (est.) are planning estimates, not quotes. Handbook facts below were read on 2026-11-17 and 2026-11-19 from the SCF Handbook (Submission Criteria, RFP Track, Budget & Deliverable Guidelines).

## 1. Summary

A shared analytics service that SCF runs for the projects it funds. Each project gets a private dashboard that combines **website visitors** (self-hosted Umami) and **API health** (OpenTelemetry traces turned into request volume, errors and latency). SCF operators get one ecosystem-wide view. Everything is open source in one monorepo, privacy-first (no cookies, no IP addresses, no wallet addresses in stored data), and hosted by us for 12 months before handover to a community operator.

## 2. Where we are today

A working prototype exists and is public. Facts, not promises:

| Built and tested (18 automated tests) | Not built yet |
|---|---|
| OpenTelemetry ingest (JSON), path normalization, per-project keys stored as hashes | Live run against a real Umami; one Umami website per project |
| Hourly aggregates kept 24 months; exact rows kept 30 days | Web-script hardening (pinned scripts with integrity hashes, bot filtering) |
| Enrollment that is closed by default (operator, invite code or hourly cap); operator remove, key rotate and revoke, full erasure | Dashboard served live by the API (the demo page is static) |
| Stellar protocol grouping, SLO and error budget, alert rules to Slack/Discord, CSV export | Onboarding guides, runbook, load test, redundant hosting |
| Umami client covering every RFP web metric | Pilot projects, tenant-perspective screen-capture video |

Requirement-by-requirement status: [docs/RFP-COVERAGE.md](docs/RFP-COVERAGE.md). Prior work is presented as exactly that; the award funds what is in the right-hand column.

## 3. Scope

### 3.1 Committed scope (what the tranches pay for)

1. **Web analytics.** Umami, unmodified and pinned by version, one website per project, tracker script served from our domain at a versioned path with a Subresource Integrity hash. Metrics: page views, unique visitors, referrers, session duration, bounce rate, country, device, browser.
2. **API analytics.** Projects dual-export OpenTelemetry to us. We keep only standardized metrics (counts and latency histograms); traces, spans and logs are discarded. Routes are normalized so wallet addresses and ids never reach the database.
3. **Per-project dashboard** (web and API together), **SCF global view**, **alert rules** with Slack/Discord webhooks, **CSV export**.
4. **Operations for SCF:** enrollment that is closed by default and opened by invite code or an hourly cap, remove a non-ecosystem project, issue, rotate and revoke keys.
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

### 3.3 Stellar use case and tech stack

The RFP asks for developer tooling for Stellar projects, so Stellar is the reason the service exists, not a storage layer. The service has **no on-chain component** (no smart contracts, no token, no wallets or keys). Its Stellar value is that it understands Stellar traffic:

- API routes are grouped by the Stellar protocol they serve: SEP-10 (auth), SEP-12 (KYC), SEP-24 (deposit and withdraw), SEP-31 (cross-border payments), Stellar RPC and Horizon. A generic tool shows `/sep24/transactions/deposit/interactive`; this one shows "SEP-24 is slow".
- Stellar addresses in paths are replaced before storage (`G…` and `M…` become `{account}`, `C…` contract ids become `{contract}`), as are transaction hashes and ids, so on-chain identities never reach the database (`normalize_path`, covered by a test).
- **Most recent stable stack:** grouping rules follow the current SEP documents and the current names in the Stellar docs. Stellar RPC was formerly called Soroban RPC; the prototype still labels the group "Soroban RPC", and tranche #1 renames it (the `/rpc` route prefix is unchanged). The rule set is versioned in the repository and reviewed at every Stellar protocol release.
- Tenants instrument with the standard OpenTelemetry SDKs for JavaScript, Go, Rust and Python, the languages most Stellar backends use; nothing Stellar-specific has to be installed.

Plain-English stack: Python service (standard library plus `psycopg`), PostgreSQL, Umami (MIT, unmodified) for web analytics, Docker or AWS Lambda for the API, AWS Lightsail in one EU region for hosting, infrastructure as code in `infra/`. Diagram: docs/TECHNICAL-ARCHITECTURE.md.

### 3.4 Decentralization: why not, and how lock-in is avoided

The RFP asks for one shared service that SCF runs, so the service is **not decentralized by design**: analytics needs one accountable data controller for GDPR, tenant isolation and erasure, and there is nothing to settle on-chain. What we do instead so no single operator is a point of capture:

- Everything is Apache-2.0 in one monorepo, including infrastructure as code, so SCF, a community operator or any project can run its own instance.
- Tenants use standard OpenTelemetry and **dual-export**: their own monitoring keeps working, and pointing the exporter elsewhere is one setting.
- Every tenant can export its data (CSV today; full export at handover), and the handover to a community operator between months 6 and 12 is tested (section 6).

## 4. Tranches and timeline

The payment schedule is the one in the SCF Budget & Deliverable Guidelines: **tranche #0 (10%) is paid on award acceptance and has no deliverables**; the three milestone tranches follow (20% MVP, 30% testnet or equivalent, 40% mainnet or equivalent). This service has no on-chain component, so the equivalents are: **#2 = staging with real pilot traffic** (the testnet equivalent) and **#3 = production launch** (the mainnet equivalent).

Every deliverable can be checked by someone outside the team: a public URL, a tagged release, a committed report, a video, or a written confirmation from a pilot. Pilot outreach starts now, before any award, because pilots depend on other people's calendars. No letters of interest exist yet at submission; any we receive are added as they arrive.

| Tranche | Share | Amount | Submitted | Milestone |
|---|---|---|---|---|
| **#0** | 10% | US$5,600 | on award acceptance | no deliverables (advance, per the SCF guidelines) |
| **#1 · MVP** | 20% | US$11,200 | month 1.5 | multi-tenant staging, per-project dashboard, hardened tracker, release with a bill of materials |
| **#2 · Pilots and scale** (testnet equivalent) | 30% | US$16,800 | month 3 | 3 web pilots and 1 API pilot live, onboarding guides, load test, threat model and monitoring plan |
| **#3 · Production launch** (mainnet equivalent) | 40% | US$22,400 | month 5 | redundant production, backup drill, failover test, scanning and alert rules, runbook and support process, 10+ projects, tested handover |
| **Operation** | | not requested | months 6-17 | 12 months of hosting and support funded by the applicant; monthly availability and security report; handover to a community operator between months 6 and 12 of operation, at SCF's discretion |

**90-day rule.** Each tranche is submitted within 90 days of the previous payment: about 45 days each for #1 and #2, and about 60 days for #3. SCF is told in advance if a date will slip, because a missed deadline without notice forfeits the remaining funds.

**Why 5 months and not 4.** The guidelines cap the timeline at 6 months and the handbook says projects typically run 3 to 6. We plan 5 because pilot onboarding and a load test depend on third parties and infrastructure that cannot be rushed, so the pilots sit in tranche #2 where they can be demonstrated. Dropping the stretch work in #2 would return the plan to 4 months.

## 5. Deliverables and the cost of each

Costs are **person-hours** (one engineer working one hour) at **US$100 an hour** (est.), the same rate for both engineers: 560 hours in total over 5 months, about 26 hours a week for the two of us together. b2bdev works about 335 hours (infrastructure, security, availability, operations) and b2bdev2 about 225 hours (ingestion, data model, API, dashboards, onboarding); the **Lead** column names who delivers each item. The work in each tranche is sized to what SCF pays for it under the 10/20/30/40 schedule: the #0 advance and the #1 payment together cover tranche #1, and the #2 and #3 payments cover their own tranches. Each tranche's cost is within US$400 of its payment (table at the end of this section).

**Tranche #1 · MVP (month 1.5): 170 h, US$17,000** (paid by #0 + #1: US$16,800)

| # | Deliverable | Lead | Hours | US$ | How reviewers verify it |
|---|---|---|---|---|---|
| 1.1 | Staging environment with TLS running the API and Umami; a provisioning script creates one Umami website per project | b2bdev | 50 | 5,000 | Public staging URL; script in the repository; tagged release |
| 1.2 | Per-project dashboard (web and API together) served by the API | b2bdev2 | 60 | 6,000 | Reviewers sign in to staging with a test project key; screenshots in the release notes |
| 1.3 | Hardened tracker: Umami pinned by version, script served from our domain at a versioned path with a Subresource Integrity hash, bot filtering | b2bdev | 40 | 4,000 | Script URL and hash published in the onboarding guide; bot-filter tests pass in CI |
| 1.4 | Release v0.2 with a software bill of materials; "Stellar RPC" naming (section 3.3) | b2bdev2 | 20 | 2,000 | GitHub release with the SBOM attached |

**Tranche #2 · Pilots and scale, testnet equivalent (month 3): 170 h, US$17,000** (paid by #2: US$16,800)

| # | Deliverable | Lead | Hours | US$ | How reviewers verify it |
|---|---|---|---|---|---|
| 2.1 | **3 SCF-funded projects on web analytics and 1 on API traffic, live**, with the web onboarding guide, a tenant-perspective screen-capture video and the live SCF global view | b2bdev2 | 85 | 8,500 | Each pilot's site or service sends data; video link; live global view shown to reviewers; written confirmation from each pilot |
| 2.2 | OpenTelemetry onboarding guides for JavaScript, Go, Rust and Python, each with a working example | b2bdev2 | 30 | 3,000 | Guides and example apps in the repository; reviewers can run an example against staging |
| 2.3 | Load test at 1,000,000 requests a day (the RFP design target) | b2bdev | 35 | 3,500 | Published report plus the load script, so reviewers can rerun it |
| 2.4 | **Threat model and monitoring plan** (required by the Submission Criteria in tranche 2), using SDF's Threat Modeling Readiness guide and monitoring-plan template, adapted to an off-chain service | b2bdev | 20 | 2,000 | Both documents committed to the repository |

**Tranche #3 · Production launch, mainnet equivalent (month 5): 220 h, US$22,000** (paid by #3: US$22,400)

| # | Deliverable | Lead | Hours | US$ | How reviewers verify it |
|---|---|---|---|---|---|
| 3.1 | Production with TLS, backups and a redundant ingestion path (two zones, load balancer, high-availability database) | b2bdev | 70 | 7,000 | Public production URL; infrastructure as code in the repository |
| 3.2 | Backup and restore drill on production | b2bdev | 15 | 1,500 | Committed drill report with timings |
| 3.3 | Failover test and measured availability report | b2bdev | 20 | 2,000 | Committed report with external uptime-check data |
| 3.4 | Continuous vulnerability scanning in CI; alert rule settings in the dashboard | b2bdev | 15 | 1,500 | CI logs; a test alert delivered to a Slack or Discord channel |
| 3.5 | Runbook, public issue tracker with templates, and the support process (section 6) | b2bdev | 20 | 2,000 | Runbook and `SUPPORT.md` in the repository; issue tracker open |
| 3.6 | 10 or more projects enrolled | b2bdev2 | 30 | 3,000 | Count shown in the global view; names listed with each project's consent |
| 3.7 | Handover plan with a tested data migration to a second environment, including the domain transfer or permanent redirect | b2bdev | 50 | 5,000 | Migration report; second environment restored from the export |

| Tranche | Hours | Cost of deliverables (US$) | Payment (US$) |
|---|---|---|---|
| #0 + #1 | 170 | 17,000 | 16,800 (5,600 + 11,200) |
| #2 | 170 | 17,000 | 16,800 |
| #3 | 220 | 22,000 | 22,400 |
| **Total** | **560** | **56,000** | **56,000** |

## 6. Service levels: what we commit to, and how we prove it

| RFP target | Our commitment |
|---|---|
| 99.99% ingestion | Designed for it: stateless ingestion on two servers in different availability zones behind a load balancer, exporters retry so short outages lose nothing. We **measure and publish** availability monthly and say plainly if the target is missed. Tranche #3 includes a failover test and a measured availability report; we do not claim a guarantee that one provider cannot give |
| 99.90% dashboards | Separate, simpler deployment with its own checks |
| Critical and high vulnerabilities patched in 24 hours | One production dependency, pinned images, daily dependency scanning, same-day release process. Two engineers in neighbouring time zones (Ecuador UTC-5, Mexico UTC-6) back each other up; b2bdev leads security response and b2bdev2 is the backup. Neither gives round-the-clock cover, so the response hours are published |
| 12 months of hosting and support | Included after tranche #3, funded by the applicant |
| Support tickets answered within 5 business days, resolved within 10 | Public GitHub issue tracker with templates (a private email address for security reports). First answer within 5 business days; fix, or a written plan with a date if it needs a release, within 10. Response times are published in the monthly report. No on-call rotation, as the RFP allows |
| Regular community status updates | A monthly public update (progress against the tranche, availability, incidents, security fixes, enrolled projects) posted in the repository, in the SCF Discord and on Bluesky with a Mastodon mirror; incident notes in the issue tracker within 2 business days |
| Handover in months 6-12 | Repository ownership transfer, full data migration (PostgreSQL and Umami), infrastructure code, runbook, and either a **domain transfer or a permanent redirect** from our domain; counted as complete only when the new operator runs the system alone for one week |

Details: [docs/OPERATIONS.md](docs/OPERATIONS.md).

## 7. Privacy, security and supply chain

- **No personal data stored.** No cookies, no IP addresses, no user agents, no query strings; wallet addresses, hashes and ids in paths are replaced by placeholders before storage. Details and the erasure workflow: [docs/PRIVACY-GDPR.md](docs/PRIVACY-GDPR.md). This is not a legal opinion; we will obtain one before launch.
- **Where we do not claim compliance without consent or local advice:** Germany (TDDDG §25 is read strictly by some authorities, so tenants there may need to load the tracker after consent), other EU states with strict ePrivacy readings, and countries with data-localisation laws that require local storage (for example Russia and China), since all data stays in the EU. Service is not offered in jurisdictions excluded by SDF's Official Rules (Cuba, Iran, North Korea and the occupied regions of Ukraine). The full list is in docs/PRIVACY-GDPR.md and is confirmed by a legal opinion before launch.
- **Data residency:** all tenant data stays in one EU region, stated publicly. Proposed: AWS Frankfurt (Germany). Before the award we confirm that Lightsail offers the managed high-availability database and load balancer there; if not, the nearest EU region that does is used.
- **Tenant isolation:** every query filtered by project; the global view shows per-project totals only; covered by automated tests.
- **Supply chain:** Umami pinned by version and image digest, unmodified; new releases reviewed by a person; signed releases with a bill of materials; tracker script versions are immutable.
- **Web hardening and bot mitigation:** [docs/WEB-ANALYTICS.md](docs/WEB-ANALYTICS.md). We state what it stops and what it does not (bots that run JavaScript, large botnets).

## 8. Adoption plan

- **Target:** 3 SCF-funded projects on web analytics and 1 on API traffic by tranche #2, shown with a tenant-perspective screen-capture video and the live global view (the RFP's proof of adoption).
- **Process:** shortlist 4 to 6 funded projects now; ask for letters of interest now (none yet at submission), because these letters are the strongest independent evidence we can show; onboard with the guide and examples. The project adds **one script tag** for web and **one extra exporter** for API (alongside its existing monitoring, which stays untouched).
- **Success criteria:** the project sees its own data within one day of starting; no personal data leaves its site; the project confirms in writing.
- **Pilot data is used** to tune the bot limits and to feed the load report.
- We list pilot names only after a letter exists.

## 9. Budget

**Requested from SCF (development, until launch)**

| Line | USD |
|---|---|
| Engineering, 5 months, two engineers (est. 560 person-hours at US$100), itemised per deliverable in section 5 | 56,000 |
| **Total request** | **56,000** |

An independent security review of authentication and tenant isolation is **not** in the request: the Budget & Deliverable Guidelines exclude audit costs, which SDF's Audit Bank covers for eligible projects. We will apply to the Audit Bank; until then, isolation is covered by automated tests and the tranche #2 threat model.

**Funded by the applicant (12 months of operation, required by the RFP)**

| Line | USD |
|---|---|
| Hosting, redundant deployment (priced below) | about 1,600 |
| Support and on-call, 12 months (est.) | 5,400 |
| **Total** | **about 7,000** |

The Budget & Deliverable Guidelines say award costs must support development and cannot cover general operations; the RFP makes the 12 months of hosting an obligation of the proposer. We therefore **do not ask SCF to fund operation**. The applicant carries about US$7,000 across the 12 months, plus about US$12 a month for a staging server while building.

**Hosting priced (AWS Lightsail pricing page, read 2026-11-17):** two 4 GB instances in different availability zones (2 x US$24), a load balancer (US$18), a 2 GB managed PostgreSQL with the high-availability plan (US$60) and about US$5 of snapshots: about US$131 a month, about US$1,570 a year. The earlier single-server design cost about US$59 a month; the difference is what the RFP's availability target costs. Details: [COSTS.md](COSTS.md).

Excluded from the request (ineligible or not needed): marketing, audits, legal and entity fees, contingency, past work, and the legal opinion on GDPR (to be quoted before launch).

## 10. Team

Two engineers working together at B2B, an Ecuador-based technology consultancy focused on AWS architecture for critical systems (https://b2b.com.ec).

**b2bdev, founder of B2B, infrastructure and operations lead.** Systems engineer (ESPE) with 18 years in software development, architecture and IT management. AWS Certified Solutions Architect – Associate and AWS Certified Cloud Practitioner. He has led B2B since 2020, delivering cloud architecture, security, capacity planning, cost optimization and support for critical systems. Previously Lead Software Architect at Ecuador's Contraloría General del Estado (the national audit office), Senior Developer and Technical Lead at Universidad Andina Simón Bolívar, and Senior Business Intelligence Developer at Uniplex Business Solutions.

**b2bdev2, data and backend lead (Mexico).** Software and data engineer with 13+ years in Python, SQL, Java and AWS (Lambda/Serverless, Glue, S3, PostgreSQL; AWS Certified Cloud Practitioner), ETL pipelines and REST APIs. He has delivered two production Python and blockchain systems that integrate on-chain and off-chain data (transaction handling, verification, auditable logging), including an election-day integrity system, and has hands-on experience integrating AI and LLMs. He wrote the prototype in this repository.

**Split of work.** b2bdev2 builds the ingestion pipeline, data model, metrics API and dashboards. b2bdev owns the AWS architecture, security hardening, availability and failover, cost control, the 12 months of hosting and the handover to a community operator. Section 5 names the lead for each deliverable and the hours of each engineer.

This repository is public evidence of delivery: a tested prototype, written requirement-by-requirement status, and documents for privacy, operations and web hardening.

**Contact:** GitHub https://github.com/kuidsh (b2bdev2). Real names and professional profiles are given in the SCF form; this public repository uses role names only.

**Track record, stated plainly.** We are new to SCF: b2bdev2 has no previous SCF or SDF award. Instead of past awards we offer evidence that can be checked: this public prototype with its automated tests and a requirement-by-requirement status that says what is still open; b2bdev's 18 years of architecture and operations for critical systems; and letters from SCF-funded pilot projects as they arrive. From the first month we publish a monthly status update, so SCF can follow delivery. Both engineers complete KYC before any payment.

## 11. Risks and how we handle them

| Risk | Mitigation |
|---|---|
| Team not yet known to SCF (no previous award) | Public prototype and tests as evidence of delivery; pilot letters as they arrive; monthly public status updates from the first month (section 10) |
| Other teams submitting for the same RFP | Differentiate on what is already running and tested, honest status reporting, and Stellar-specific insight (protocol grouping, SLO) |
| No pilots secured yet | Outreach starts now; letters added as they arrive; the pilots sit in tranche #2, not earlier |
| Security review not funded by the award (audits are ineligible costs) | Apply to SDF's Audit Bank; tenant isolation covered by automated tests; threat model in tranche #2 |
| Stellar naming or protocol changes (for example Soroban RPC renamed to Stellar RPC) | Grouping rules versioned in the repository and reviewed at each Stellar protocol release |
| 99.99% ingestion on a small budget | Redundant deployment priced (about US$131 a month); availability measured, reported and not guaranteed |
| 24-hour patching with a two-person team | Automation, two engineers who back each other up, published response hours |
| Operating costs may not be eligible | Not requested: the applicant funds the 12 months of operation (section 9) |
| Privacy compliance depends on law and jurisdiction | Documented position, legal review before launch, no overclaiming |
| Umami behaviour not yet verified on a live instance | First task of tranche #1; documented fallback to the GoatCounter adapter |
| XLM price moves between award and payment | Awards are valued in USD at the payment-day price (per the handbook); convert on receipt |
| Plan is 5 months while the handbook speaks of about 4 months of development | Within the typical 3 to 6 months and the 6-month cap; stretch work in tranche #2 can be dropped to return to 4 |

## 12. Alternatives and sustainability

| Alternative | Why it does not meet this RFP on its own |
|---|---|
| Google Analytics and other ad-funded tools | Cookies and personal data; consent banners; data leaves the ecosystem's control |
| Hosted privacy tools (Plausible Cloud, Fathom) | Paid per site; no API analytics; no SCF-wide view |
| Self-hosted Umami or GoatCounter alone | Web only; no OpenTelemetry API metrics, no tenant model for SCF, no operator controls |
| APM products (Datadog, Grafana Cloud, New Relic) | Paid per host or per event; keep traces and identifiers; know nothing about SEPs or Stellar RPC |
| Other teams' prototypes for this RFP | Public prototypes exist. Ours is differentiated by what is already built and tested: Stellar protocol grouping, an SLO with error budget, Slack and Discord alerts, CSV export, 1-hour to 1-year views from 24-month rollups, operator controls (rotate, revoke, erase), and a requirement-by-requirement status that says what is still open |

**Sustainability.** The RFP requires zero fees, so there is no revenue model. The award funds development; the applicant funds the 12 months of operation (section 9). Running costs are published (about US$131 a month for the redundant deployment) so a successor operator can budget for them, and the handover in months 6 to 12 moves the service to a community operator chosen by SCF.

## 13. KPIs

Projects enrolled; projects live on web and on API; weekly active dashboards; ingestion availability (measured, against 99.99%); dashboard availability (against 99.90%); time to patch critical and high vulnerabilities; p95 ingest latency; alert rules in use; time for a new project to see its first data.
