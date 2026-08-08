from pathlib import Path

MIGRATION = (
    Path(__file__).parents[3]
    / "supabase"
    / "migrations"
    / "20260808000004_tenant_owned_financial_metric_catalog.sql"
)


def test_catalog_migration_is_once_only_and_service_role_installed() -> None:
    sql = MIGRATION.read_text(encoding="utf-8")

    assert "CREATE TABLE IF NOT EXISTS financial_metric_catalog_installations" in sql
    assert "tenant_id UUID PRIMARY KEY" in sql
    assert "ON CONFLICT DO NOTHING" in sql
    assert "auth.role() IS DISTINCT FROM 'service_role'" in sql
    assert "REVOKE ALL ON FUNCTION install_financial_metric_catalog" in sql
    assert "TO service_role" in sql


def test_catalog_migration_preserves_confirmed_delete_boundary() -> None:
    sql = MIGRATION.read_text(encoding="utf-8")

    assert "current_setting('app.metric_delete_confirmed', TRUE)" in sql
    assert "Use the confirmed financial metric deletion workflow" in sql
    assert "IF OLD.is_system AND" not in sql
    assert "'blocked_by_system', FALSE" in sql
    assert "'can_delete', COALESCE((impact->>'blocker_total')::INTEGER, 0) = 0" in sql


def test_existing_metrics_are_not_replaced_and_receive_legacy_marker() -> None:
    sql = MIGRATION.read_text(encoding="utf-8")

    assert "SET origin = 'legacy_default'" in sql
    assert "SELECT DISTINCT tenant_id, 'legacy-v1'" in sql
    assert "WHERE origin = 'legacy_default'" not in sql
    assert "origin, catalog_version, is_system, is_active" in sql
