import os

import pytest

from scripts.verify_rls import connect, fetch_table_statuses, load_environment, summarize


def test_public_tables_have_rls_and_tenant_scoped_policies() -> None:
    load_environment()
    if not os.environ.get("DATABASE_URL"):
        pytest.skip("DATABASE_URL is required for RLS metadata verification")

    with connect() as conn:
        summary = summarize(fetch_table_statuses(conn))

    assert summary["blocker_count"] == 0, summary["blockers"]
