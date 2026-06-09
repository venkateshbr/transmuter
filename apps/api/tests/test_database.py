from app.core import database


def test_supabase_schema_is_public_for_cloud_target(monkeypatch) -> None:
    monkeypatch.setattr(database.settings, "supabase_target", "cloud")

    assert database.get_supabase_schema() == "public"
    assert database.get_supabase_client_options().schema == "public"


def test_supabase_schema_is_transmuter_for_local_target(monkeypatch) -> None:
    monkeypatch.setattr(database.settings, "supabase_target", "local")

    assert database.get_supabase_schema() == "transmuter"
    assert database.get_supabase_client_options().schema == "transmuter"
