from pathlib import Path

MIGRATION_PATH = (
    Path(__file__).resolve().parents[3]
    / "supabase"
    / "migrations"
    / "20260711000001_harden_rls_identity_claims.sql"
)


def test_rls_identity_helpers_use_canonical_security_definer_lookup() -> None:
    migration = MIGRATION_PATH.read_text()

    assert migration.count("SECURITY DEFINER") == 2
    assert migration.count("SET search_path = pg_catalog, %1$I") == 2
    assert migration.count("platform_user.id = auth.uid()") == 2
    assert migration.count("platform_user.status = 'active'") == 2
    assert "authorization_key TEXT := 'transmuter_authorization_' || current_schema()" in migration
    assert "user_metadata" not in migration


def test_rls_identity_helpers_require_complete_matching_claim_pairs() -> None:
    migration = MIGRATION_PATH.read_text()

    assert migration.count("token.claims -> 'app_metadata' -> %2$L ->> 'tenant_id'") == 2
    assert migration.count("token.claims -> 'app_metadata' -> %2$L ->> 'role'") == 2
    assert migration.count("token.claims -> 'app_metadata' -> %2$L IS NULL") == 2
    assert migration.count("token.claims ->> 'tenant_id'") == 2
    assert migration.count("token.claims ->> 'app_role'") == 2
    assert migration.count("= platform_user.tenant_id::TEXT") == 4
    assert migration.count("= platform_user.role") == 4


def test_rls_identity_helper_execution_is_restricted_to_runtime_roles() -> None:
    migration = MIGRATION_PATH.read_text()

    assert migration.count("FROM PUBLIC, anon, authenticated, service_role") == 2
    assert migration.count("TO authenticated, service_role") == 2
