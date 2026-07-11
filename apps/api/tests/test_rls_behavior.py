from __future__ import annotations

# ruff: noqa: E402, I001

import json
import os
from uuid import UUID, uuid4

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
    user_id = uuid4()

    with _connect_database() as conn:
        with conn.cursor() as cur:
            _seed_tenants_and_business_units(cur, tenant_a, tenant_b)
            _seed_user(cur, user_id, tenant_a, role="transformation_office")
            _act_as_user(
                cur,
                user_id,
                {
                    "app_metadata": {
                        _authorization_key(): {
                            "tenant_id": str(tenant_a),
                            "role": "transformation_office",
                        }
                    }
                },
            )

            cur.execute("select name from business_units order by name")

            assert cur.fetchall() == [("Tenant A Unit",)]
        conn.rollback()


def test_wrong_tenant_insert_is_blocked_by_rls() -> None:
    tenant_a = uuid4()
    tenant_b = uuid4()
    user_id = uuid4()

    with _connect_database() as conn:
        with conn.cursor() as cur:
            _seed_tenants_and_business_units(cur, tenant_a, tenant_b)
            _seed_user(cur, user_id, tenant_a, role="transformation_office")
            _act_as_user(
                cur,
                user_id,
                {
                    "app_metadata": {
                        _authorization_key(): {
                            "tenant_id": str(tenant_a),
                            "role": "transformation_office",
                        }
                    }
                },
            )

            _assert_insert_blocked(cur, tenant_b)
        conn.rollback()


@pytest.mark.parametrize("mismatch", ["tenant", "tenant_format", "role"])
def test_mismatched_authorization_claims_have_no_rls_identity(mismatch: str) -> None:
    tenant_a = uuid4()
    tenant_b = uuid4()
    user_id = uuid4()
    claim_tenant_id = str(tenant_b if mismatch == "tenant" else tenant_a)
    if mismatch == "tenant_format":
        claim_tenant_id = f"{{{claim_tenant_id}}}"
    claim_role = "viewer" if mismatch == "role" else "transformation_office"

    with _connect_database() as conn:
        with conn.cursor() as cur:
            _seed_tenants_and_business_units(cur, tenant_a, tenant_b)
            _seed_user(cur, user_id, tenant_a, role="transformation_office")
            _act_as_user(
                cur,
                user_id,
                {
                    "app_metadata": {
                        _authorization_key(): {
                            "tenant_id": claim_tenant_id,
                            "role": claim_role,
                        }
                    },
                    "tenant_id": str(tenant_a),
                    "app_role": "transformation_office",
                    "user_metadata": {
                        "tenant_id": str(tenant_a),
                        "role": "transformation_office",
                    },
                },
            )

            _assert_rls_identity_rejected(cur, tenant_a)
        conn.rollback()


def test_user_metadata_only_claims_have_no_rls_identity() -> None:
    tenant_a = uuid4()
    tenant_b = uuid4()
    user_id = uuid4()

    with _connect_database() as conn:
        with conn.cursor() as cur:
            _seed_tenants_and_business_units(cur, tenant_a, tenant_b)
            _seed_user(cur, user_id, tenant_a, role="transformation_office")
            _act_as_user(
                cur,
                user_id,
                {
                    "app_metadata": {"provider": "email"},
                    "user_metadata": {
                        "tenant_id": str(tenant_a),
                        "role": "transformation_office",
                    },
                },
            )

            _assert_rls_identity_rejected(cur, tenant_a)
        conn.rollback()


@pytest.mark.parametrize("present_key", ["tenant_id", "role"])
def test_partial_app_metadata_does_not_fall_back_to_legacy_claims(
    present_key: str,
) -> None:
    tenant_a = uuid4()
    tenant_b = uuid4()
    user_id = uuid4()
    app_metadata = {
        _authorization_key(): {
            present_key: (str(tenant_a) if present_key == "tenant_id" else "transformation_office")
        }
    }

    with _connect_database() as conn:
        with conn.cursor() as cur:
            _seed_tenants_and_business_units(cur, tenant_a, tenant_b)
            _seed_user(cur, user_id, tenant_a, role="transformation_office")
            _act_as_user(
                cur,
                user_id,
                {
                    "app_metadata": app_metadata,
                    "tenant_id": str(tenant_a),
                    "app_role": "transformation_office",
                },
            )

            _assert_rls_identity_rejected(cur, tenant_a)
        conn.rollback()


def test_wrong_schema_authorization_scope_has_no_rls_identity() -> None:
    tenant_a = uuid4()
    tenant_b = uuid4()
    user_id = uuid4()

    with _connect_database() as conn:
        with conn.cursor() as cur:
            _seed_tenants_and_business_units(cur, tenant_a, tenant_b)
            _seed_user(cur, user_id, tenant_a, role="transformation_office")
            _act_as_user(
                cur,
                user_id,
                {
                    "app_metadata": {
                        "transmuter_authorization_wrong_schema": {
                            "tenant_id": str(tenant_a),
                            "role": "transformation_office",
                        }
                    }
                },
            )

            _assert_rls_identity_rejected(cur, tenant_a)
        conn.rollback()


@pytest.mark.parametrize("identity", ["inactive", "unknown"])
def test_inactive_or_unknown_user_has_no_rls_identity(identity: str) -> None:
    tenant_a = uuid4()
    tenant_b = uuid4()
    canonical_user_id = uuid4()
    token_user_id = uuid4() if identity == "unknown" else canonical_user_id

    with _connect_database() as conn:
        with conn.cursor() as cur:
            _seed_tenants_and_business_units(cur, tenant_a, tenant_b)
            _seed_user(
                cur,
                canonical_user_id,
                tenant_a,
                role="transformation_office",
                user_status="deactivated" if identity == "inactive" else "active",
            )
            _act_as_user(
                cur,
                token_user_id,
                {
                    "app_metadata": {
                        _authorization_key(): {
                            "tenant_id": str(tenant_a),
                            "role": "transformation_office",
                        }
                    }
                },
            )

            _assert_rls_identity_rejected(cur, tenant_a)
        conn.rollback()


def test_matching_legacy_signed_claims_resolve_canonical_rls_identity() -> None:
    tenant_a = uuid4()
    tenant_b = uuid4()
    user_id = uuid4()

    with _connect_database() as conn:
        with conn.cursor() as cur:
            _seed_tenants_and_business_units(cur, tenant_a, tenant_b)
            _seed_user(cur, user_id, tenant_a, role="transformation_office")
            _act_as_user(
                cur,
                user_id,
                {
                    "tenant_id": str(tenant_a),
                    "app_role": "transformation_office",
                },
            )

            cur.execute("select current_tenant_id(), current_user_role()")
            assert cur.fetchone() == (tenant_a, "transformation_office")
            cur.execute("select name from business_units order by name")
            assert cur.fetchall() == [("Tenant A Unit",)]
        conn.rollback()


def _connect_database() -> psycopg.Connection:
    conn = psycopg.connect(settings.database_url)
    db_schema = _configured_schema()
    with conn.cursor() as cur:
        cur.execute(
            sql.SQL("set search_path to {}, public, extensions").format(sql.Identifier(db_schema))
        )
    return conn


def _configured_schema() -> str:
    return os.environ.get("DB_SCHEMA", DEFAULT_DB_SCHEMA).strip() or DEFAULT_DB_SCHEMA


def _authorization_key() -> str:
    return f"transmuter_authorization_{_configured_schema()}"


def _seed_tenants_and_business_units(cur: psycopg.Cursor, tenant_a: UUID, tenant_b: UUID) -> None:
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


def _seed_user(
    cur: psycopg.Cursor,
    user_id: UUID,
    tenant_id: UUID,
    *,
    role: str,
    user_status: str = "active",
) -> None:
    email = f"rls-{user_id}@example.invalid"
    cur.execute(
        """
        insert into auth.users (
          instance_id,
          id,
          aud,
          role,
          email,
          encrypted_password,
          email_confirmed_at,
          raw_app_meta_data,
          raw_user_meta_data,
          created_at,
          updated_at,
          confirmation_token,
          email_change,
          email_change_token_new,
          recovery_token
        )
        values (
          '00000000-0000-0000-0000-000000000000',
          %s,
          'authenticated',
          'authenticated',
          %s,
          '',
          now(),
          '{}'::jsonb,
          '{}'::jsonb,
          now(),
          now(),
          '',
          '',
          '',
          ''
        )
        """,
        (user_id, email),
    )
    cur.execute(
        """
        insert into users (id, tenant_id, email, role, status)
        values (%s, %s, %s, %s, %s)
        """,
        (user_id, tenant_id, email, role, user_status),
    )


def _act_as_user(
    cur: psycopg.Cursor, user_id: UUID, authorization_claims: dict[str, object]
) -> None:
    claims = {"sub": str(user_id), "role": "authenticated", **authorization_claims}
    cur.execute("set local role authenticated")
    cur.execute("select set_config(%s, %s, true)", ("request.jwt.claims", json.dumps(claims)))


def _assert_rls_identity_rejected(cur: psycopg.Cursor, tenant_id: UUID) -> None:
    cur.execute("select current_tenant_id(), current_user_role()")
    assert cur.fetchone() == (None, None)
    cur.execute("select name from business_units order by name")
    assert cur.fetchall() == []
    _assert_insert_blocked(cur, tenant_id)


def _assert_insert_blocked(cur: psycopg.Cursor, tenant_id: UUID) -> None:
    cur.execute("savepoint rejected_rls_insert")
    with pytest.raises(psycopg.errors.InsufficientPrivilege):
        cur.execute(
            """
            insert into business_units (tenant_id, name, code)
            values (%s, %s, %s)
            """,
            (tenant_id, "Rejected RLS Unit", "REJECTED"),
        )
    cur.execute("rollback to savepoint rejected_rls_insert")
