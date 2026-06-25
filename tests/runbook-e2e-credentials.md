# Transmuter Runbook E2E — Tenant Login Credentials (Second Pass)

Environment: **dev** — https://transmuter-dev.ishirock.tech (login at `/auth/login`)
Stripe: sandbox (test card `4242 4242 4242 4242`, any future expiry/CVC).
All tenants created via real public signup + checkout. Role of each admin: `transformation_office`.

> These are throwaway dev test tenants. Same password is reused across scenarios for easy validation.

**Shared password (all scenarios):** `Transmuter#E2E2026`

| Scenario | Tenant (org) | Slug | Admin email | Currency / FY | Tenant ID |
|---|---|---|---|---|---|
| 7 — Pinnacle Professional Services | Pinnacle Professional Services | `pinnacle` | `pinnacle.to@transmuter-e2e.dev` | USD / Jan | `f9641073-e754-4dbd-9038-47c61c20bbb6` |
| 2 — Aurelia Retail Holdings | Aurelia Retail Holdings | `aurelia` | `aurelia.to@transmuter-e2e.dev` | GBP / Apr → **USD / Jan** (F14) | `4d1cec5d-d8fe-4fb3-9b6c-0e6bcbd4e663` |
| 3 — Nordvik Manufacturing | Nordvik Manufacturing | `nordvik` | `nordvik.to@transmuter-e2e.dev` | EUR / Jan → **USD / Jan** (F14) | `935b5ee1-ee8b-4d4a-aaf5-63f609f8beba` |
| 5 — Cascade Financial Services | Cascade Financial Services | `cascade` | `cascade.to@transmuter-e2e.dev` | AUD / Jul → **USD / Jan** (F14) | `cf850726-bdd7-490b-b3fe-a848ac20a5da` |
| 6 — Verdant Agritech | Verdant Agritech | `verdant` | `verdant.to@transmuter-e2e.dev` | BRL / Jan → **USD / Jan** (F14) | `6bf98baa-9b57-4f76-b77e-6918ee637e2b` |
| 4 — Helios Health Systems | Helios Health Systems | `helios` | `helios.to@transmuter-e2e.dev` | USD / Oct → **USD / Jan** (F14: fiscal only) | `da1682a8-cea7-4c4a-b78c-777ed359bea5` |
| 1 — Meridian Logistics Group | Meridian Logistics Group | `meridian` | `meridian.to@transmuter-e2e.dev` | SGD / Jan → **USD / Jan** (F14: currency only) | `13aa1b04-e939-43ee-8323-46c0f0ed35db` |
| 8 — Stellar Media & Entertainment | Stellar Media & Entertainment | `stellar` | `stellar.to@transmuter-e2e.dev` | USD / Jan (no F14 impact) | `db01be51-ab48-429f-babd-79e1ebcaa00e` |

_Rows added as each scenario is built. To validate: open the dev URL → Login → use the admin email + shared password above._
