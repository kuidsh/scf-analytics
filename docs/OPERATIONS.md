# Operations: availability, patching, handover (design, not yet deployed)

## Targets from the RFP

| Target | Value |
|---|---|
| Ingestion availability | 99.99% (about 52 minutes of downtime a year) |
| Dashboard availability | 99.90% (about 8.8 hours a year) |
| Critical and high vulnerabilities | patched within 24 hours |
| Hosting | 12 months after the final tranche |
| Support tickets | answered within 5 business days, resolved within 10; no mandatory on-call; a public issue tracker is enough |
| Handover | to a community operator between months 6 and 12: repository ownership, full data migration, and a domain transfer or permanent redirect |

The earlier draft promised 99.5% ingest uptime. That is below the RFP and has been replaced in PROPOSAL.md.

## What 99.99% ingestion needs

A single server cannot meet it. The design:

- **Ingestion path separated from the dashboards.** Stateless API handlers (the same code runs as AWS Lambda behind an HTTP API, or as containers) in at least two availability zones. Lambda plus HTTP API is already defined in `infra/template.yaml`; the priced deployment below uses the container option on Lightsail.
- **Buffering on failure.** OpenTelemetry exporters retry. Tenants are told to keep the default retry settings so a short outage loses nothing.
- **Database:** a managed PostgreSQL with a standby in a second zone and automated backups. Dashboards read from it; losing the standby must not stop ingestion.
- **Dashboards and Umami** on a separate, simpler deployment with the lower 99.90% target.
- **External uptime checks** from outside the platform, feeding the same alert webhook the tenants use.

**Cost (AWS Lightsail pricing page, read 2026-11-17):**

| Item | USD per month |
|---|---|
| 2 x 4 GB instances in different availability zones | 48 |
| Load balancer | 18 |
| Managed PostgreSQL 2 GB, high-availability plan | 60 |
| Snapshots and backups (estimate) | 5 |
| **Total** | **about 131 (about 1,570 a year)** |

The single-server tier (one 4 GB instance, standard 2 GB database, about US$59 a month) is used for staging and demos only, never for production. Region (Frankfurt proposed) is a deployment setting; confirm availability of the high-availability database and load balancer there before the award. The applicant funds operation; it is not part of the request to SCF.

## Patching within 24 hours

- Dependencies are few (one production dependency, `psycopg`) and pinned.
- CI runs the test suite and a dependency vulnerability scan on every pull request and daily.
- A critical or high finding opens an issue assigned to the operator; the fix is released by tag and deployed the same day. Container images are pinned by digest so a rebuild is deliberate.

## Support (designed)

- **Where:** the public GitHub issue tracker, with templates for bugs, onboarding help and enrollment requests. Security reports go to a private email address (published in `SECURITY.md`), never to a public issue.
- **How fast:** first answer within 5 business days; a fix, or a written plan with a date if it needs a release, within 10 business days. Critical and high vulnerabilities follow the 24-hour rule above.
- **No on-call rotation** (the RFP does not require one). Response hours and the backup operator are published.
- Response times are reported in the monthly update.

## Community status updates (designed)

- A monthly public update: progress against the current tranche, measured availability, incidents, security fixes, enrolled projects, response times.
- Posted in the repository (Discussions or a `STATUS.md` log), in the SCF Discord, and on Bluesky with a Mastodon mirror.
- Incident notes in the issue tracker within 2 business days of an outage.

## Handover (months 6-12)

Checklist: repository ownership transfer, the AWS account or the infrastructure-as-code needed to recreate it, the domain (**transferred, or our domain permanently redirects to the new one**), the secrets inventory (rotated at handover), full data migration (`pg_dump` plus the Umami export, restored and checked in the new environment), the runbook, and a one-week overlap where both operators have access. Tranche #3 includes a rehearsal: a tested data migration to a second environment.

## Runbook (to write in tranche #3)

Deploy, rollback, restore from backup, rotate the admin token, rotate a tenant key, remove a tenant, and respond to a firing alert.
