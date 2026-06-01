# Pilot Seed Data

This directory contains deterministic seed data for the Hostinger/local Supabase pilot instance. Run it after the schema migration has created the `transmuter` schema and after all application migrations have been applied.

```bash
psql "$TARGET_DATABASE_URL" -v ON_ERROR_STOP=1 \
  -f scripts/pilot/202606010001_seed_pilot_data.sql
```

Default pilot login:

```text
admin@ishirock.dev / Transmuter2026!
```

## Required Pilot Coverage

The pilot dataset is intentionally broad enough for real API and browser acceptance tests. It seeds:

- Supabase Auth users plus Transmuter application users for admin, initiative owner, viewer, finance, and risk roles.
- One tenant organization with an active subscription.
- Business units, workstreams, and workstream user memberships.
- Financial configuration groups and items for benefit, cost, and shared-cost selections.
- Five initiatives across revenue, automation, procurement, people, and controls workstreams.
- Initiative team assignments, milestones, milestone dependencies, risks, status updates, KPIs, and KPI entries.
- Financial entries, cost lines, financial selections, shared-cost pools, allocation rules, allocation runs, and allocations.
- Recurring meetings, sessions, attendees, meeting-initiative links, agenda items, action items, and artifacts.
- Initiative dependencies and value-realization notes.

The SQL resets only the fixed pilot tenant (`11111111-1111-4111-8111-111111111111`) before reseeding, so it can be rerun without touching other tenants.
