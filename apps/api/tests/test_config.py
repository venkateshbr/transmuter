import pytest

from app.core.config import Settings

SUPABASE_ENV_KEYS = (
    "SUPABASE_TARGET",
    "SUPABASE_URL",
    "SUPABASE_ANON_KEY",
    "SUPABASE_SERVICE_KEY",
    "SUPABASE_CLOUD_URL",
    "SUPABASE_CLOUD_ANON_KEY",
    "SUPABASE_CLOUD_SERVICE_KEY",
    "SUPABASE_LOCAL_URL",
    "SUPABASE_LOCAL_ANON_KEY",
    "SUPABASE_LOCAL_SERVICE_KEY",
    "SUPABASE_SCHEMA",
    "DATABASE_URL",
    "DATABASE_CLOUD_URL",
    "DATABASE_LOCAL_URL",
)


@pytest.fixture(autouse=True)
def clear_supabase_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for key in SUPABASE_ENV_KEYS:
        monkeypatch.delenv(key, raising=False)


def _settings(**values: str) -> Settings:
    return Settings(
        _env_file=None,
        jwt_secret="x" * 32,
        openrouter_api_key="sk-test",
        **values,
    )


def test_cloud_target_resolves_cloud_supabase_and_database_settings() -> None:
    settings = _settings(
        supabase_target="cloud",
        supabase_cloud_url="https://cloud.supabase.co",
        supabase_cloud_anon_key="cloud-anon",
        supabase_cloud_service_key="cloud-service",
        database_cloud_url="postgresql://cloud/postgres",
    )

    assert settings.supabase_target == "cloud"
    assert settings.supabase_url == "https://cloud.supabase.co"
    assert settings.supabase_anon_key == "cloud-anon"
    assert settings.supabase_service_key == "cloud-service"
    assert settings.database_url == "postgresql://cloud/postgres"


def test_local_target_resolves_local_supabase_and_database_settings() -> None:
    settings = _settings(
        supabase_target="local",
        supabase_local_url="https://supabase.ishirock.tech",
        supabase_local_anon_key="local-anon",
        supabase_local_service_key="local-service",
        database_local_url=(
            "postgresql://postgres:secret@host.docker.internal:5432/postgres"
            "?options=-csearch_path%3Dtransmuter,public,extensions"
        ),
    )

    assert settings.supabase_target == "local"
    assert settings.supabase_url == "https://supabase.ishirock.tech"
    assert settings.supabase_anon_key == "local-anon"
    assert settings.supabase_service_key == "local-service"
    assert settings.database_url.endswith("search_path%3Dtransmuter,public,extensions")


def test_target_specific_values_take_precedence_over_legacy_values() -> None:
    settings = _settings(
        supabase_target="local",
        supabase_url="https://legacy-cloud.supabase.co",
        supabase_anon_key="legacy-anon",
        supabase_service_key="legacy-service",
        database_url="postgresql://legacy/postgres",
        supabase_local_url="https://supabase.ishirock.tech",
        supabase_local_anon_key="local-anon",
        supabase_local_service_key="local-service",
        database_local_url="postgresql://local/postgres",
    )

    assert settings.supabase_url == "https://supabase.ishirock.tech"
    assert settings.supabase_anon_key == "local-anon"
    assert settings.supabase_service_key == "local-service"
    assert settings.database_url == "postgresql://local/postgres"


def test_legacy_direct_supabase_envs_still_work_without_target_specific_values() -> None:
    settings = _settings(
        supabase_url="https://legacy.supabase.co",
        supabase_anon_key="legacy-anon",
        supabase_service_key="legacy-service",
        database_url="postgresql://legacy/postgres",
    )

    assert settings.supabase_target == "cloud"
    assert settings.supabase_url == "https://legacy.supabase.co"
    assert settings.supabase_anon_key == "legacy-anon"
    assert settings.supabase_service_key == "legacy-service"
    assert settings.database_url == "postgresql://legacy/postgres"


def test_empty_supabase_settings_are_allowed_for_deterministic_no_db_tests() -> None:
    settings = _settings()

    assert settings.supabase_target == "cloud"
    assert settings.supabase_url == ""
    assert settings.supabase_anon_key == ""
    assert settings.supabase_service_key == ""


def test_partial_supabase_settings_still_fail_fast() -> None:
    with pytest.raises(ValueError, match="Missing required Supabase setting"):
        _settings(supabase_url="https://legacy.supabase.co")
