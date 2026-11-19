# Web analytics: Umami, and how it is hardened

## Why Umami and not GoatCounter

Both are open source, cookieless and lightweight. We choose **Umami** because:

1. **Same database as the API metrics.** Umami runs on PostgreSQL, so one managed PostgreSQL serves the whole platform: one backup policy, one patching routine, one thing to hand over to a community operator.
2. **Multiple sites with a REST API.** One Umami website per enrolled project, read through its REST API (`scfa/umami.py`), so each tenant dashboard can show web and API data together without a second login.
3. **MIT licence**, used unmodified, which keeps the monorepo licence story simple.
4. **Ecosystem familiarity.** It is the option the RFP names first and the one other applicants are also likely to know how to operate.

Trade-offs we accept: Umami is a Node.js application with a heavier footprint than GoatCounter's single Go binary. If the operator prefers the lighter footprint, only `scfa/umami.py` (about 70 lines) would change. GoatCounter's licence and API details must be re-checked before any switch.

## Metrics delivered

Page views, unique visitors, visits, referrers, average session duration, bounce rate, country, device and browser, all from Umami's `/stats` and `/metrics` endpoints (see `web_summary()`).

## Hardening plan (designed; to be built and verified in tranche #1)

| RFP concern | Plan |
|---|---|
| Frontend-only collection | One `<script>` tag per site. No backend integration, no server-side events. |
| Version-pinned tracking scripts | The tracker file is served from our own domain at a versioned path (`/t/v1.js`). A change publishes a new path and a new Subresource Integrity hash; old paths keep working, so a tenant never silently runs new code. |
| Supply-chain defences | The Umami image is pinned by digest, not by `latest`. The script is built from the pinned release, never fetched at runtime from a third party. Update PRs are reviewed by a human; the `latest` tag is never deployed. Tenants add the script with `integrity="sha384-..."` so a tampered file fails to load. |
| Ad-blocker-resistant naming | Serve the script and collection endpoint from a first-party path on our domain with a non-obvious name. Umami has settings for renaming the tracker and its collection endpoint; confirm the exact names in the pinned version. |
| Bot and inflation mitigation | Umami ignores common bot user agents at collection (verify in the pinned version). On top: rate limits per IP at the reverse proxy (Caddy), an allow-list of the domains each website may report from, and dropping hits whose referrer or hostname does not match the registered domain. |
| Tenant isolation | One Umami website per project; read-only share links; the API only ever uses the website id stored on the project's own row. |

Nothing in this table is claimed as built. The status column in [RFP-COVERAGE.md](RFP-COVERAGE.md) is the source of truth.
