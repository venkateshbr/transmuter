import os

import pytest

from scripts.verify_rls import (
    connect,
    fetch_table_statuses,
    get_db_schema,
    load_environment,
    summarize,
)


def test_configured_schema_tables_have_rls_and_tenant_scoped_policies() -> None:
    load_environment()
    if not os.environ.get("DATABASE_URL"):
        pytest.skip("DATABASE_URL is required for RLS metadata verification")

    schema = get_db_schema()
    with connect() as conn:
        summary = summarize(fetch_table_statuses(conn, schema), schema)

    assert summary["schema"] == schema
    assert summary["blocker_count"] == 0, summary["blockers"]


def test_db_schema_env_selects_supported_schema(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DB_SCHEMA", "transmuter")

    assert get_db_schema() == "transmuter"
