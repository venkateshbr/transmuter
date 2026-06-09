"""Verify tenant RLS coverage for Supabase launch readiness.

This script reads only PostgreSQL catalog metadata. It does not inspect row data.
"""

from __future__ import annotations

import json
import os
import sys
from dataclasses import asdict, dataclass
from pathlib import Path

import psycopg
from dotenv import load_dotenv
from psycopg.rows import dict_row

DEFAULT_DB_SCHEMA = "public"
SUPPORTED_DB_SCHEMAS = {"public", "transmuter"}

IGNORED_TABLES = {
    "spatial_ref_sys",
}

# Tenant-root tables do not carry tenant_id because their primary key is the tenant.
TENANT_ROOT_TABLES = {
    "organizations",
}

# Tables that are intentionally global reference/config data.
GLOBAL_REFERENCE_TABLES = {
    "gate_criteria",
}

TENANT_POLICY_MARKERS = (
    "tenant_id",
    "auth.uid",
    "auth.jwt",
    "current_setting",
    "jwt",
)


@dataclass(frozen=True)
class TableRlsStatus:
    table: str
    has_tenant_id: bool
    rls_enabled: bool
    rls_forced: bool
    policy_count: int
    tenant_policy_count: int
    classification: str
    severity: str
    notes: list[str]


def load_environment() -> None:
    repo_root = Path(__file__).resolve().parents[3]
    api_root = Path(__file__).resolve().parents[1]
    load_dotenv(repo_root / ".env")
    load_dotenv(api_root / ".env", override=True)


def connect() -> psycopg.Connection:
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        raise RuntimeError("DATABASE_URL is required to verify PostgreSQL RLS metadata.")
    return psycopg.connect(database_url, row_factory=dict_row)


def get_db_schema() -> str:
    schema = os.environ.get("DB_SCHEMA", DEFAULT_DB_SCHEMA).strip() or DEFAULT_DB_SCHEMA
    if schema not in SUPPORTED_DB_SCHEMAS:
        raise RuntimeError(
            f"DB_SCHEMA must be one of {', '.join(sorted(SUPPORTED_DB_SCHEMAS))}."
        )
    return schema


def fetch_table_statuses(conn: psycopg.Connection, schema: str | None = None) -> list[TableRlsStatus]:
    db_schema = schema or get_db_schema()
    with conn.cursor() as cur:
        cur.execute(
            """
            select
                c.relname as table_name,
                c.relrowsecurity as rls_enabled,
                c.relforcerowsecurity as rls_forced,
                exists (
                    select 1
                    from pg_attribute a
                    where a.attrelid = c.oid
                      and a.attname = 'tenant_id'
                      and not a.attisdropped
                ) as has_tenant_id
            from pg_class c
            join pg_namespace n on n.oid = c.relnamespace
            where n.nspname = %s
              and c.relkind in ('r', 'p')
            order by c.relname
            """,
            (db_schema,),
        )
        table_rows = cur.fetchall()

        cur.execute(
            """
            select
                tablename as table_name,
                policyname,
                coalesce(qual, '') as using_expression,
                coalesce(with_check, '') as check_expression
            from pg_policies
            where schemaname = %s
            order by tablename, policyname
            """,
            (db_schema,),
        )
        policies_by_table: dict[str, list[dict[str, object]]] = {}
        for policy in cur.fetchall():
            policies_by_table.setdefault(str(policy["table_name"]), []).append(policy)

    statuses: list[TableRlsStatus] = []
    for row in table_rows:
        table = str(row["table_name"])
        if table in IGNORED_TABLES:
            continue

        has_tenant_id = bool(row["has_tenant_id"])
        rls_enabled = bool(row["rls_enabled"])
        rls_forced = bool(row["rls_forced"])
        policies = policies_by_table.get(table, [])
        tenant_policy_count = 0
        for policy in policies:
            expression = " ".join(
                [
                    str(policy["using_expression"]).lower(),
                    str(policy["check_expression"]).lower(),
                ]
            )
            if any(marker in expression for marker in TENANT_POLICY_MARKERS):
                tenant_policy_count += 1

        classification = "tenant"
        notes: list[str] = []
        if table in TENANT_ROOT_TABLES:
            classification = "tenant-root"
            notes.append("Tenant root table; primary key is the tenant boundary.")
        elif table in GLOBAL_REFERENCE_TABLES:
            classification = "global-reference"
            notes.append("Global reference/config table; tenant_id is not expected.")

        severity = "pass"
        if classification == "tenant":
            if not has_tenant_id:
                severity = "blocker"
                notes.append("Tenant-scoped table is missing tenant_id.")
            if not rls_enabled:
                severity = "blocker"
                notes.append("RLS is not enabled.")
            if len(policies) == 0:
                severity = "blocker"
                notes.append("No RLS policies are defined.")
            elif tenant_policy_count == 0:
                severity = "blocker"
                notes.append("Policies do not appear to contain tenant/JWT scoping.")
        else:
            if not rls_enabled:
                severity = "warning"
                notes.append("Launch review should confirm this non-tenant table is intentionally public to service-role clients.")
            elif len(policies) == 0:
                severity = "warning"
                notes.append("RLS is enabled but no policies are defined.")

        statuses.append(
            TableRlsStatus(
                table=table,
                has_tenant_id=has_tenant_id,
                rls_enabled=rls_enabled,
                rls_forced=rls_forced,
                policy_count=len(policies),
                tenant_policy_count=tenant_policy_count,
                classification=classification,
                severity=severity,
                notes=notes,
            )
        )

    return statuses


def summarize(statuses: list[TableRlsStatus], schema: str | None = None) -> dict[str, object]:
    blockers = [status for status in statuses if status.severity == "blocker"]
    warnings = [status for status in statuses if status.severity == "warning"]
    tenant_tables = [status for status in statuses if status.classification == "tenant"]
    return {
        "schema": schema or get_db_schema(),
        "table_count": len(statuses),
        "tenant_table_count": len(tenant_tables),
        "pass_count": len([status for status in statuses if status.severity == "pass"]),
        "warning_count": len(warnings),
        "blocker_count": len(blockers),
        "blockers": [asdict(status) for status in blockers],
        "warnings": [asdict(status) for status in warnings],
    }


def main() -> int:
    load_environment()
    schema = get_db_schema()
    with connect() as conn:
        statuses = fetch_table_statuses(conn, schema)

    summary = summarize(statuses, schema)
    print(json.dumps(summary, indent=2, sort_keys=True))

    if summary["blocker_count"]:
        return 1
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"RLS verification failed: {exc}", file=sys.stderr)
        raise SystemExit(2) from exc
