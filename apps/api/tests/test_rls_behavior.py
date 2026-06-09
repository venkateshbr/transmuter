from __future__ import annotations

# ruff: noqa: E402, I001

import json
import os
from uuid import uuid4

import psycopg
import pytest
from dotenv import load_dotenv
from psycopg import sql

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "../../../.env"))

from app.core.config import settings  # noqa: E402


DEFAULT_DB_SCHEMA = "public"


pytestmark = pytest.mark.skipif(
    not settings.database_url,
    reason="DATABASE_URL is required for live PostgreSQL RLS behavior tests.",
)


def test_cross_tenant_select_is_filtered_by_rls_claims() -> None:
    tenant_a = uuid4()
    tenant_b = uuid4()

    with _connect_database() as conn:
        with conn.cursor() as cur:
            _seed_tenants_and_business_units(cur, tenant_a, tenant_b)
            _act_as_tenant(cur, tenant_a)

            cur.execute("select name from business_units order by name")

            assert cur.fetchall() == [("Tenant A Unit",)]
        conn.rollback()


def test_wrong_tenant_insert_is_blocked_by_rls() -> None:
    tenant_a = uuid4()
    tenant_b = uuid4()

    with _connect_database() as conn:
        with conn.cursor() as cur:
            _seed_tenants_and_business_units(cur, tenant_a, tenant_b)
            _act_as_tenant(cur, tenant_a)

            cur.execute("savepoint wrong_tenant_insert")
            with pytest.raises(psycopg.errors.InsufficientPrivilege):
                cur.execute(
                    """
                    insert into business_units (tenant_id, name, code)
                    values (%s, %s, %s)
                    """,
                    (tenant_b, "Wrong Tenant Unit", "WRONG"),
                )
            cur.execute("rollback to savepoint wrong_tenant_insert")
        conn.rollback()


def _connect_database() -> psycopg.Connection:
    conn = psycopg.connect(settings.database_url)
    db_schema = os.environ.get("DB_SCHEMA", DEFAULT_DB_SCHEMA).strip() or DEFAULT_DB_SCHEMA
    with conn.cursor() as cur:
        cur.execute(
            sql.SQL("set search_path to {}, public, extensions").format(
                sql.Identifier(db_schema)
            )
        )
    return conn


def _seed_tenants_and_business_units(
    cur: psycopg.Cursor, tenant_a: object, tenant_b: object
) -> None:
    cur.execute(
        """
        insert into organizations (id, name, slug)
        values (%s, %s, %s), (%s, %s, %s)
        """,
        (
            tenant_a,
            "RLS Tenant A",
            f"rls-tenant-a-{tenant_a}",
            tenant_b,
            "RLS Tenant B",
            f"rls-tenant-b-{tenant_b}",
        ),
    )
    cur.execute(
        """
        insert into business_units (tenant_id, name, code)
        values (%s, %s, %s), (%s, %s, %s)
        """,
        (
            tenant_a,
            "Tenant A Unit",
            "A",
            tenant_b,
            "Tenant B Unit",
            "B",
        ),
    )


def _act_as_tenant(cur: psycopg.Cursor, tenant_id: object) -> None:
    claims = {
        "role": "authenticated",
        "user_metadata": {
            "tenant_id": str(tenant_id),
            "role": "transformation_office",
        },
    }
    cur.execute("set local role authenticated")
    cur.execute("select set_config(%s, %s, true)", ("request.jwt.claims", json.dumps(claims)))
