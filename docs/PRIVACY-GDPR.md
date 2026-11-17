# Privacy and GDPR (not legal advice)

## Position: no consent banner needed because no personal data is stored

| Surface | What is stored | What is not |
|---|---|---|
| API analytics (this repo) | project id, normalized route, HTTP method, status code, latency, timestamp (hourly aggregates, plus 30 days of flat request rows) | IP addresses, user agents, query strings, bodies, headers, user or wallet identifiers, trace ids, span ids |
| Web analytics (Umami) | aggregate page views, visits, referrers, country, device, browser | cookies, raw IP addresses, cross-site identifiers. Umami derives a visitor id by hashing and does not store the IP; confirm this against the pinned version's documentation before relying on it |

Identifiers inside request paths (wallet addresses, hashes, numeric ids, UUIDs, long tokens) are replaced by placeholders before storage (`normalize_path`), so a route such as `/accounts/G...` is stored as `/accounts/{account}`.

Whether data without personal data needs opt-in is a legal judgement. Take advice from a data-protection lawyer before launch.

## Data residency

Choose the hosting region deliberately and publish it. Default plan: one EU region for the managed PostgreSQL and the server, so data never leaves the EU; tenants outside the EU are informed in the onboarding guide. The region is a deployment setting in `infra/`, not a code change.

## Erasure workflow

1. A project asks for erasure (or SCF removes a non-ecosystem project).
2. An operator calls `DELETE /v1/admin/projects/<id>` with the admin token. This deletes the project row, its raw request rows, its hourly rollups and its alert rules in one transaction.
3. The operator deletes the matching Umami website in the Umami admin UI (its API supports this too).
4. The operator confirms to the requester. Backups age out on the backup retention schedule (state it in the runbook).

Because no personal data is stored, a data-subject erasure request about an individual visitor normally cannot be matched to any record; the workflow above covers tenant-level deletion.

## Retention

Raw request rows: 30 days. Hourly aggregates: 24 months (the RFP asks for at least 24 months of aggregated views). Both are constants in `scfa/store.py` and are purged by the scheduled job.
