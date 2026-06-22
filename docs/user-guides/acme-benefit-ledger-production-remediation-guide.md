# ACME Benefit Ledger Production Remediation

This guide explains how to recreate the ACME benefit realization ledger through
the UI using the deployed Benefit Tracking ledger editor/import feature.

## Location

Open `Dashboard > Benefit Tracking` or navigate directly to
`/financials/benefit-tracking`.

Use:
- `Ledger Entries` to add or edit individual rows.
- `Import` to upload CSV rows in bulk.

The CSV import does not require `bankable_plan_amount`. The system derives the
locked plan amount from each initiative's current bankable plan.

Use `docs/user-guides/acme-benefit-ledger-import.csv` for the exact ACME import
payload. It contains 240 monthly rows:
- 10 ACME initiatives.
- 2027 and 2028.
- 12 months per initiative per year.

For ACME4, the current platform generates `TRN-001` through `TRN-010` initiative
codes rather than the historical `ENT-*` codes in the CSV. Before importing into
ACME4, replace `ENT-001` with `TRN-001`, `ENT-002` with `TRN-002`, and continue
through `ENT-010` to `TRN-010`. The maintained browser runner
`apps/web/e2e/acme4-full-demo-ui-e2e.mjs` performs this mapping automatically
before uploading the ledger.

## Prerequisites

For each ACME initiative, complete governance approvals through the UI until the
initiative has an approved Gate 2 submission and a locked Bankable Plan.

Recommended UI path:
1. Open `Initiatives > Pipeline`.
2. Open an initiative.
3. Open the `Governance` tab.
4. Submit and approve gates sequentially through Gate 2.
5. Continue through Gate 4 if the initiative should remain in `executing`.
6. Verify `Dashboard > Bankable Plan` shows a locked plan for the initiative.

## CSV Format

Required columns:

```csv
initiative_code,period_granularity,period_start,period_end,actual_amount,description
```

Use `monthly` granularity. Create one row per initiative per month for 2027 and
2028, or upload `docs/user-guides/acme-benefit-ledger-import.csv`.

## ACME Monthly Actual Amounts

For each initiative/year below, create 12 monthly rows:
- `period_start`: first day of the month.
- `period_end`: last day of the month.
- `description`: `Seeded ACME <year> monthly realization for <initiative_code>; actuals mirror financial-engine actual scenario.`

| Initiative | 2027 monthly actual | 2028 monthly actual |
|---|---:|---:|
| ENT-001 | 3583.3333 | 7500.0000 |
| ENT-002 | 36625.0000 | 81416.6667 |
| ENT-003 | 25466.6667 | 48500.0000 |
| ENT-004 | 66250.0000 | 133333.3333 |
| ENT-005 | 19733.3333 | 44666.6667 |
| ENT-006 | 37266.6667 | 78750.0000 |
| ENT-007 | 21500.0000 | 48750.0000 |
| ENT-008 | 50816.6667 | 99916.6667 |
| ENT-009 | 31416.6667 | 66750.0000 |
| ENT-010 | 31775.0000 | 70416.6667 |

## Example Rows

```csv
initiative_code,period_granularity,period_start,period_end,actual_amount,description
ENT-001,monthly,2027-01-01,2027-01-31,3583.3333,Seeded ACME 2027 monthly realization for ENT-001; actuals mirror financial-engine actual scenario.
ENT-001,monthly,2027-02-01,2027-02-28,3583.3333,Seeded ACME 2027 monthly realization for ENT-001; actuals mirror financial-engine actual scenario.
ENT-001,monthly,2028-01-01,2028-01-31,7500.0000,Seeded ACME 2028 monthly realization for ENT-001; actuals mirror financial-engine actual scenario.
```

## Validation

After import:
1. Open `Dashboard > Benefit Tracking > Summary` or
   `/financials/benefit-tracking`.
2. Set scope to `Portfolio`.
3. Set granularity to `Monthly` or `Yearly`.
4. Confirm locked baseline, realized benefit, and variance are non-zero.
5. Set scope to `Initiative` and spot-check `ENT-001`, `ENT-005`, and `ENT-010`
   for legacy ACME tenants, or `TRN-001`, `TRN-005`, and `TRN-010` for ACME4.
6. Re-upload the same CSV once to verify upsert behavior: the result should show
   updated rows rather than duplicate created rows.
7. Run the ACME annual-baseline scenario against production.
