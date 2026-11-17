# Cost model (all USD)

## Starting investment (not AWS)

| Item | Cost | Status |
|---|---|---|
| SCF application | 0 | No fee found in the SCF Handbook |
| Testnet / tooling | 0 | Open-source tools only |
| Domain for the hosted service (optional) | ~12/yr | Estimate, can wait until award |
| **Total before award** | **0–12** | |

## AWS, monthly

Prices from the AWS Lightsail pricing page (read 2026-11-15).

| Phase | Service | Size | USD/mo |
|---|---|---|---|
| Before award (optional live demo) | Lightsail instance | 2 GB RAM, 2 vCPU, 60 GB SSD, 3 TB transfer | 12 |
| Production | Lightsail instance (Umami + API) | 4 GB RAM, 2 vCPU, 80 GB SSD, 4 TB transfer | 24 |
| Production | Lightsail managed database, standard | 2 GB RAM, 80 GB SSD, encrypted | 30 |
| Production | Snapshots / S3 backups | allowance | 5 (estimate) |
| **Production total** | | | **≈ 59/mo ≈ 708/yr** |

The RFP asks the proposer to host the service for 12 months, so the 12-month
hosting cost (≈ US$708, budgeted at US$1,200 with headroom for growth) is a line
in the grant budget, not an out-of-pocket cost.

Source: https://aws.amazon.com/lightsail/pricing/

## Revenue and payback

SCF Build Awards are paid in XLM in four tranches: 10% on award, 20% at MVP,
30% at testnet, 40% at mainnet launch (SCF v7 page). SCF #45 funded 40 projects
for ≈ US$4.04M of XLM (≈ US$101k average; our division).

| Draft request | Tranche 0 (10%, on award) | Covers |
|---|---|---|
| US$64,000 | US$6,400 | Start cost + 108 months of production AWS |

Payback depends entirely on winning an award. Timing risk: SCF #45 closed
2026-08-16 and results were public by 2026-09-30 (~6.5 weeks). If round #47
closes in early-to-mid January 2027, an award would land around late February
or early March 2027, close to the end of the 3-month window.
