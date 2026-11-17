# RFP coverage: what is built, what is designed, what is open

RFP: "Web and API Analytics for Stellar Ecosystem Projects"
(<https://stellar.gitbook.io/scf-handbook/scf-awards/build-award/rfp-track#current-open-rfps>).
Requirements below are paraphrased from the handbook; re-read the source before submitting.

Status: **Built** = code and a passing test in this repo. **Designed** = written down here, not implemented. **Open** = not done.

| RFP requirement | Status | Where |
|---|---|---|
| Pick Umami or GoatCounter and justify it | Designed | [WEB-ANALYTICS.md](WEB-ANALYTICS.md) |
| Self-service enrollment | Built | `POST /v1/enroll`, closed by default; opened by invite code or rate limit; `test_enrollment_is_closed_by_default_and_gated` |
| SCF can remove non-ecosystem projects | Built | `DELETE /v1/admin/projects/<id>` (removes all data) |
| Strict tenant isolation, global view for SCF | Built | every query filtered by `project_id`; `/v1/global` needs the admin token |
| Zero fees | Designed | no billing code exists; stated in PROPOSAL.md |
| API key generation and revocation by SCF operators | Built | `rotate-key` and `revoke-key` admin routes |
| OSI-approved licence | Built | Apache-2.0 |
| Web metrics: page views, unique visitors, referrers, session duration, bounce rate, country, device, browser | Built (client) / Open (live Umami) | `scfa/umami.py` `web_summary()`, `test_web_summary_has_every_rfp_web_metric`; not yet run against a live Umami |
| Web: frontend-only collection, bot mitigation, version-pinned scripts, supply-chain defences, ad-blocker-resistant naming | Designed | [WEB-ANALYTICS.md](WEB-ANALYTICS.md) |
| GDPR without opt-in, data residency, erasure workflow | Designed + erasure Built | [PRIVACY-GDPR.md](PRIVACY-GDPR.md); API erasure is `DELETE /v1/admin/projects/<id>` |
| API: tenants dual-export OpenTelemetry | Built | `POST /v1/traces` (OTLP/HTTP JSON; protobuf is Open) |
| API: collector discards traces/spans, keeps standard metrics, stores in PostgreSQL | Built (with a caveat) | no trace or span ids are stored. A short-lived flat request row (30 days) is kept for exact percentiles and alerts; long-term storage is aggregates only |
| API: path normalization with a default rule set | Built | `scfa/otlp.py` `normalize_path`, `test_path_normalization_hides_ids_and_addresses` |
| Design target about 1,000,000 requests/day | Open | the proposal commits to a load test at this rate in stage T2; not run yet |
| Aggregated views kept at least 24 months | Built | hourly rollups, `ROLLUP_RETENTION_DAYS = 730`, `test_rollups_outlive_raw_rows_and_serve_long_windows` |
| 99.99% ingestion / 99.90% dashboard availability | Designed | [OPERATIONS.md](OPERATIONS.md) (redundant deployment designed and priced at about US$131 a month; not built) |
| Critical/high vulnerabilities patched within 24 h | Designed | [OPERATIONS.md](OPERATIONS.md) |
| Handover to a community operator in months 6-12 | Designed | [OPERATIONS.md](OPERATIONS.md) |
| Monorepo with IaC, runbooks, onboarding guide, tests, security/privacy docs, monitoring | Partly | IaC and tests exist; runbook and onboarding guide are Open |
| Proof of adoption: 3 SCF projects on web analytics, 1 on API, demo videos | Open | needs pilots; see PROPOSAL.md |
| Track record with SCF/SDF (weighted heavily; unknown builders excluded) | Open | applicant's own history; nothing in this repo can supply it |
| Budget | n/a | the RFP states none; our request is US$57,400 for development, an estimate. Operation is funded by the applicant |
