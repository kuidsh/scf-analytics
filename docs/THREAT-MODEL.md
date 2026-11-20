# Threat model (draft)

Draft, 19 November 2026. This covers the prototype in this repository and the service the proposal plans. It says what is **in place** (code plus a passing test, or a setting in the repository), what is **planned** (with the tranche that delivers it) and what is **open** (no plan committed yet). Tranche #2 (deliverable 2.4 in [PROPOSAL.md](../PROPOSAL.md)) completes it against SDF's Threat Modeling Readiness guide and adds the monitoring plan. Nothing is deployed yet, so no threat here has been tested against a live system.

It follows the four usual questions: what are we building, what can go wrong, what are we doing about it, and did we do a good enough job.

## 1. What we are building

A shared analytics service that SCF runs for the projects it funds. It has **no on-chain component**: no smart contracts, no wallets, no Stellar keys, no funds. Architecture: [TECHNICAL-ARCHITECTURE.md](TECHNICAL-ARCHITECTURE.md).

**Trust boundaries**

| # | Boundary | Who crosses it | Authentication today |
|---|---|---|---|
| B1 | Tenant backend → ingest (`POST /v1/traces`) | A project's OpenTelemetry exporter | Project key in `x-scfa-key`, looked up by SHA-256 hash |
| B2 | Tenant team → their own metrics (`GET /v1/metrics`) | The project's developers | The same project key |
| B3 | SCF operator → global view and admin routes | SCF operators | One shared `ADMIN_TOKEN` in `x-scfa-admin`, compared in constant time |
| B4 | Anyone → enrollment (`POST /v1/enroll`) | Prospective projects | Closed by default; an invite code or the operator token, or open with an hourly cap |
| B5 | Visitors' browsers → web analytics (Umami tracker and collection endpoint) | The public, on tenants' websites | None (public by nature); the tracker script runs on tenants' pages |
| B6 | Scheduler → outbound alert webhooks | The 5-minute alert job | Outbound only, to Slack or Discord URLs |
| B7 | Services → PostgreSQL, Umami admin | The API, Umami, operators | Database password; Umami login |

**Assets, most sensitive first**

1. **The tracker script.** It runs on every tenant's website, so tampering with it would reach every tenant's visitors. This is the highest-impact asset.
2. **Tenant metrics.** Each project's traffic, errors and latency are confidential to that project; one tenant must never see another's.
3. **Credentials:** the operator token, project keys, invite codes, database and Umami passwords, and webhook URLs (anyone holding a Slack or Discord webhook URL can post to that channel).
4. **Availability and integrity of ingestion:** the RFP targets 99.99% for ingestion and 99.90% for dashboards; inflated or forged numbers mislead SCF.
5. **The repository, domain and cloud account,** since control of any of them hands over the service.

**What is deliberately not stored** (this limits the impact of most threats): IP addresses, user agents, cookies, query strings, trace and span ids, and wallet addresses, hashes, ids and UUIDs in paths. Details: [PRIVACY-GDPR.md](PRIVACY-GDPR.md).

## 2. What can go wrong, and what we do about it

STRIDE category: **S**poofing, **T**ampering, **R**epudiation, **I**nformation disclosure, **D**enial of service, **E**levation of privilege.

| ID | Threat | STRIDE | In place today | Planned or open |
|---|---|---|---|---|
| T1 | One tenant reads another tenant's metrics | I | Every query filters by `project_id`; the global view returns per-project totals only, no routes. Tests: `test_api_ingest_and_metrics_are_tenant_isolated`, `test_global_view_requires_admin` | Proposed: run the isolation tests on PostgreSQL in CI as well as SQLite; independent review through SDF's Audit Bank |
| T2 | A project key leaks (committed to a repository, logged by a proxy) | S | Keys are random (`secrets.token_urlsafe`), prefixed `scfa_`, shown once and stored only as SHA-256; operators can rotate or revoke one. Test: `test_self_service_enrollment_and_operator_controls` | A leaked key can read that project's metrics and send it traces, nothing more. Onboarding guides (tranche #2) say to keep the key in the exporter's environment, not in code |
| T3 | Forged or inflated API traffic, from a leaked key or a dishonest tenant | T | Bodies over 5 MB are rejected (HTTP 413). The SAM template throttles the API at 100 requests a second, burst 200 (not deployed) | **Open:** no per-key rate limit; a key holder can inflate its own project's numbers. The global view should flag sudden jumps; decided in the tranche #2 threat model |
| T4 | The operator token leaks or is guessed | E, S | Constant-time comparison (`hmac.compare_digest`); without the token, admin routes return 401. Test: `test_global_view_requires_admin` | **Open:** one shared token, no per-operator identity. Proposed for production: one token per operator, rotation at handover (already in [OPERATIONS.md](OPERATIONS.md)) |
| T5 | Operator actions cannot be traced to a person (who deleted a project?) | R | None | **Open:** append-only audit log of admin actions (who, when, which project). Proposed with T4 |
| T6 | Mass enrollment by strangers to fill the database or impersonate SCF projects | S, D | Enrollment closed by default; invite codes compared in constant time; invite and open modes capped at 10 projects an hour (429 after). Tests: `test_enrollment_is_closed_by_default_and_gated`. Operators remove non-ecosystem projects | In place |
| T7 | Personal data reaches storage | I | Only SERVER spans kept; query strings stripped; Stellar addresses, hashes, numeric ids, UUIDs and long tokens in paths replaced. Tests: `test_parse_keeps_only_server_spans_and_strips_query`, `test_path_normalization_hides_ids_and_addresses` | **Residual:** identifiers matching none of these patterns, such as an e-mail address or a user name in a path segment, would be stored. Proposed: an e-mail pattern in `normalize_path` and a warning in the onboarding guides (tranche #2); tenants can be erased on request |
| T8 | The tracker script is changed (compromised build, compromised server, malicious Umami release) | T | Not built | Tranche #1: script served from our domain at a versioned, immutable path with a Subresource Integrity hash; Umami pinned by image digest; upgrades reviewed by a person. With SRI, a changed script is refused by visitors' browsers. Plan: [WEB-ANALYTICS.md](WEB-ANALYTICS.md) |
| T9 | Bots inflate web analytics | T | Not built | Tranche #1: bot filtering, per-IP rate limits at the proxy (IPs not stored), allowed domains per website. **Residual:** bots that run JavaScript and large botnets are not stopped; this is stated publicly |
| T10 | Umami admin taken over (default login `admin` / `umami`) | E | Every document that mentions the default login says to change it on first login and never to expose it publicly; the Docker Compose file publishes ports 3000 and 8080 for local testing and warns never to expose them to the internet | Tranche #1: the provisioning script sets a strong password; the Umami admin is not reachable from the internet; tenants get read-only share links |
| T11 | Alert webhooks used to reach internal addresses (SSRF) or to leak data | I, E | Webhook URLs are set only by operators, directly in the database; there is no API to set them. The alert body holds only the project id, metric, value, threshold and time window | Tranche #3 (deliverable 3.4) adds alert settings to the dashboard: only `https` URLs on Slack and Discord webhook hosts will be accepted, with no redirects followed |
| T12 | CSV export opens with a formula (a route beginning with `=`, `+`, `-` or `@`) | T | Route names come from the tenant's own traces and are exported only to that tenant | **Open:** cells starting with those characters are not escaped yet. Proposed fix: prefix them with `'` |
| T13 | Ingestion flooded or slowed (large or many requests) | D | 5 MB body limit; API Gateway throttling in the template | Tranche #2: load test at 1,000,000 requests a day with a published report; tranche #3: redundant ingestion in two zones behind a load balancer, failover test |
| T14 | Database or backups exposed | I | Keys stored only as hashes; no personal data stored by design | Tranche #3 (deliverables 3.1, 3.2): managed PostgreSQL not publicly reachable, TLS to the database, encrypted backups, and a restore drill |
| T15 | A vulnerable dependency or image | T, E | One production dependency (`psycopg`); standard-library core | Tranche #1: bill of materials with each release; tranche #3: vulnerability scanning in CI; critical and high fixed within 24 hours ([OPERATIONS.md](OPERATIONS.md)) |
| T16 | Takeover of the GitHub, cloud or domain account | E | Repository public; no secrets committed | Two-factor authentication on every account and a registrar lock on the domain, confirmed in the tranche #2 monitoring plan; all secrets rotated at handover |
| T17 | Traffic read or changed in transit | I, T | The local development server is plain HTTP, listens on all interfaces and is meant for local testing only; nothing is deployed | Tranche #1: TLS on every public endpoint (staging and production) |

**Out of scope:** the tenants' own systems and monitoring (they dual-export, so ours is never in their critical path); the Stellar network (we hold no keys and send no transactions); visitors' browsers beyond the tracker script.

## 3. Monitoring plan (outline; completed in tranche #2)

| What is watched | What triggers action | Who responds, how fast |
|---|---|---|
| `/healthz` and the ingest endpoint, from an external uptime check | Two failed checks in a row | b2bdev leads, b2bdev2 is the backup; working hours published; incident note within 2 business days |
| Ingest error rate and p95 latency (the service's own metrics, with the same alert rules tenants use) | Error rate above 1% or p95 above 1 s for 5 minutes | Same |
| Admin routes answering 401, and enrollment answering 403 or 429 | A spike against the normal rate | Same; rotate the token or invite codes if it looks like guessing |
| Security advisories for the pinned dependencies and images | Any critical or high advisory | Patched within 24 hours |
| TLS certificate expiry, database storage, backup success | 14 days before expiry; 80% storage; any failed backup | Same |

The thresholds above are first guesses, to be set from pilot traffic in tranche #2.

## 4. Did we do a good enough job?

- The threat model is reviewed at the end of every tranche and with any change to authentication, enrollment or storage.
- Every "in place" item names its test, or the file that shows it where no test applies (documentation, configuration); an item moves from planned to in place only when a test or a published report proves it.
- We will apply to SDF's Audit Bank for an independent review of authentication and tenant isolation (audits are not in the award request).
- Security issues go to a private address published in `SECURITY.md` (added with the support process in tranche #3), never to a public issue.
