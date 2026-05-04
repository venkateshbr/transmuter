# Stripe Product Catalog Recommendation

This catalog is designed for the first launch of Transmuter as a multi-tenant enterprise transformation SaaS platform.

## Recommendation

Use a simple banded subscription catalog for launch, with manual enterprise qualification above 100 users. Transformation programs are value-heavy and executive-facing, so a very low per-user price would understate the product and make support, onboarding, AI usage, and implementation guidance hard to fund.

| Stripe product | Customer fit | User band | Monthly price | Annual price | Checkout behavior |
| --- | --- | ---: | ---: | ---: | --- |
| Transmuter Team | Pilot or smaller transformation office | 1-50 users | 999 USD / month | 9,990 USD / year | Self-serve Checkout |
| Transmuter Business | Mid-size enterprise transformation program | 51-100 users | 1,999 USD / month | 19,990 USD / year | Self-serve Checkout |
| Transmuter Enterprise | Large enterprise or complex operating model | 101+ users | Custom | Custom | Contact sales |

## Why This Catalog

- It keeps the signup path simple while the product is early.
- It maps to how buyers think: program size, not nickel-and-dime seat math.
- It preserves room for onboarding, support, AI usage, and executive reporting value.
- It lets enterprise deals include SSO/SAML, custom data controls, dedicated onboarding, custom terms, and premium support.

## Stripe Setup

Create one Stripe product named `Transmuter Platform`.

Create four recurring Prices:

| Price key | Stripe billing model | Amount | Interval |
| --- | --- | ---: | --- |
| `transmuter_team_monthly` | Flat rate | 999 USD | Monthly |
| `transmuter_team_annual` | Flat rate | 9,990 USD | Yearly |
| `transmuter_business_monthly` | Flat rate | 1,999 USD | Monthly |
| `transmuter_business_annual` | Flat rate | 19,990 USD | Yearly |

For production, store the resulting Stripe Price IDs in environment variables and have Checkout use those Price IDs. Keep the current inline `price_data` flow only for sandbox validation until production Prices exist.

## Future Option

If we want exact user-count billing later, Stripe supports per-seat and tiered recurring pricing. For launch, fixed bands are easier for buyers to approve and easier for us to support.
