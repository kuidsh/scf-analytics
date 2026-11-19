# Cost model (all USD)

## Starting investment (not AWS)

| Item | Cost | Status |
|---|---|---|
| SCF application | 0 | No fee found in the SCF Handbook |
| Testnet / tooling | 0 | Open-source tools only |
| Domain for the hosted service (optional) | ~12/yr | Estimate, can wait until award |
| **Total before award** | **0–12** | |

## AWS, monthly: single-server tier (staging and demos only)

Prices from the AWS Lightsail pricing page (read 2026-11-15). **This tier is for staging and demos. It is not the production design, because one server cannot meet the RFP's 99.99% ingestion target.** The production design is the redundant deployment in the next section.

| Phase | Service | Size | USD/mo |
|---|---|---|---|
| Before award (optional live demo) | Lightsail instance | 2 GB RAM, 2 vCPU, 60 GB SSD, 3 TB transfer | 12 |
| Staging, single server | Lightsail instance (Umami + API) | 4 GB RAM, 2 vCPU, 80 GB SSD, 4 TB transfer | 24 |
| Staging, single server | Lightsail managed database, standard | 2 GB RAM, 80 GB SSD, encrypted | 30 |
| Staging, single server | Snapshots / S3 backups | allowance | 5 (estimate) |
| **Single-server total** | | | **≈ 59/mo ≈ 708/yr** |

Source: https://aws.amazon.com/lightsail/pricing/

## Production: redundant deployment (the design the proposal budgets)

Prices from the AWS Lightsail pricing page (read 2026-11-17).

| Service | Size | USD/mo |
|---|---|---|
| Lightsail instances x2 (different availability zones) | 4 GB RAM each | 48 |
| Lightsail load balancer | | 18 |
| Lightsail managed database, high-availability plan | 2 GB RAM | 60 |
| Snapshots / backups | allowance | 5 (estimate) |
| **Total** | | **≈ 131/mo ≈ 1,570/yr** |

The single-server design above (≈ 59/mo) cannot reach the RFP's 99.99% ingestion
target; this one is designed for it, and availability is measured and published
rather than guaranteed. The proposal asks SCF to fund development only (US$56,000);
the 12 months of hosting (≈ 1,600) and support (≈ 5,400) are funded by the applicant.

## Revenue and payback

SCF Build Awards are paid in XLM in four payments: #0 10% on award acceptance (no
deliverables), #1 20% at MVP, #2 30% at testnet or equivalent, #3 40% at mainnet
or equivalent (SCF Budget & Deliverable Guidelines, read 2026-11-19). SCF #45 funded 40 projects
for ≈ US$4.04M of XLM (≈ US$101k average; our division).

| Draft request | Tranche 0 (10%, on award) | Covers |
|---|---|---|
| US$56,000 (development only) | US$5,600 | Start cost + 42 months of the redundant deployment, or about 94 months of the single server |

Payback depends entirely on winning an award. Timing risk: SCF #45 closed
2026-08-16 and results were public by 2026-09-30 (~6.5 weeks). If round #47
closes in early-to-mid January 2027, an award would land around late February
or early March 2027, close to the end of the 3-month window.
