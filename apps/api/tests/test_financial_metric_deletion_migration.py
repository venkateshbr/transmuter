from pathlib import Path

MIGRATION = (
    Path(__file__).parents[3]
    / "supabase"
    / "migrations"
    / "20260808000003_financial_metric_deletion.sql"
)


def test_metric_deletion_migration_has_transactional_guard_and_catalog_gate() -> None:
    sql = MIGRATION.read_text(encoding="utf-8")

    assert "CREATE OR REPLACE FUNCTION financial_metric_deletion_impact" in sql
    assert "CREATE OR REPLACE FUNCTION delete_financial_metric_definition" in sql
    assert "FOR UPDATE;" in sql
    assert "current_setting('app.metric_delete_confirmed', TRUE)" in sql
    assert "financial_metric_definitions_protect_delete" in sql
    assert "constraint_row.confdeltype" in sql


def test_metric_references_restrict_except_disclosed_tenant_baseline_cleanup() -> None:
    sql = MIGRATION.read_text(encoding="utf-8")

    restrict_constraints = (
        "financial_metric_formula_dependencies_input_fk",
        "financial_bridge_metric_memberships_metric_fk",
        "initiative_financial_selections_metric_tenant_fk",
        "financial_config_items_metric_tenant_fk",
        "financial_benefit_lines_metric_tenant_fk",
        "financial_metric_values_metric_tenant_fk",
        "initiative_financial_scope_metric_tenant_fk",
        "financial_initiative_annual_baselines_metric_tenant_fk",
        "shared_cost_rules_metric_tenant_fk",
        "shared_cost_allocations_metric_tenant_fk",
    )
    for constraint in restrict_constraints:
        definition = sql.split(f"CONSTRAINT {constraint}", maxsplit=1)[1].split(";", maxsplit=1)[0]
        assert "ON DELETE RESTRICT" in definition

    tenant_cleanup = sql.split(
        "CONSTRAINT financial_tenant_annual_baselines_metric_tenant_fk",
        maxsplit=1,
    )[1].split(";", maxsplit=1)[0]
    assert "ON DELETE CASCADE" in tenant_cleanup


def test_named_metric_constraints_are_safe_to_reapply() -> None:
    sql = MIGRATION.read_text(encoding="utf-8")

    recreated_constraints = (
        "financial_benefit_lines_metric_tenant_fk",
        "financial_metric_values_metric_tenant_fk",
        "initiative_financial_scope_metric_tenant_fk",
        "financial_initiative_annual_baselines_metric_tenant_fk",
        "financial_tenant_annual_baselines_metric_tenant_fk",
        "shared_cost_rules_metric_tenant_fk",
        "shared_cost_allocations_metric_tenant_fk",
    )
    for constraint in recreated_constraints:
        assert f"DROP CONSTRAINT IF EXISTS {constraint}" in sql
