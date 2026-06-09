from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # App
    app_name: str = "Transmuter API"
    version: str = "0.1.0"
    debug: bool = False

    # Supabase
    supabase_target: str = "cloud"
    supabase_url: str = ""
    supabase_anon_key: str = ""
    supabase_service_key: str = ""
    supabase_cloud_url: str = ""
    supabase_cloud_anon_key: str = ""
    supabase_cloud_service_key: str = ""
    supabase_local_url: str = ""
    supabase_local_anon_key: str = ""
    supabase_local_service_key: str = ""

    # Auth
    jwt_secret: str
    jwt_algorithm: str = "HS256"
    jwt_expiry_minutes: int = 60
    max_request_body_bytes: int = 10 * 1024 * 1024
    auth_login_rate_limit: int = 10
    auth_login_rate_window_seconds: int = 60
    public_registration_enabled: bool = False
    registration_invite_token: str = ""

    # LLM
    openrouter_api_key: str
    openrouter_base_url: str = "https://openrouter.ai/api/v1"
    default_model: str = "anthropic/claude-sonnet-4-6"

    # Langfuse
    langfuse_secret_key: str = ""
    langfuse_public_key: str = ""
    langfuse_host: str = "https://cloud.langfuse.com"
    logfire_token: str = ""
    environment: str = "development"
    sentry_dsn: str = ""
    sentry_traces_sample_rate: float = 0.1
    alert_webhook_url: str = ""
    api_p99_slo_ms: float = 2000.0
    agent_latency_slo_ms: float = 12000.0
    agent_correction_rate_slo: float = 0.10
    app_public_url: str = "http://localhost:4300"

    # Procrastinate (PostgreSQL connection string)
    database_url: str = ""
    database_cloud_url: str = ""
    database_local_url: str = ""

    # Notifications
    resend_api_key: str = ""
    resend_from_email: str = ""

    # Microsoft Graph (optional)
    microsoft_graph_access_token: str = ""
    microsoft_graph_user_id: str = ""

    # Feature flags
    ai_enabled: bool = True
    bootstrap_demo_data_on_registration: bool = False

    # Billing / payments
    payment_provider: str = ""
    stripe_secret_key: str = ""
    stripe_publishable_key: str = ""
    stripe_webhook_secret: str = ""
    stripe_price_team_monthly: str = ""
    stripe_price_team_annual: str = ""
    stripe_price_business_monthly: str = ""
    stripe_price_business_annual: str = ""
    encryption_key: str = ""

    # SaaS operator access
    platform_admin_emails: str = ""

    @model_validator(mode="after")
    def resolve_supabase_target(self) -> "Settings":
        target = self.supabase_target.strip().lower() or "cloud"
        if target not in {"cloud", "local"}:
            raise ValueError("SUPABASE_TARGET must be either 'cloud' or 'local'.")

        self.supabase_target = target
        self.supabase_url = self._target_value(target, "supabase", "url", self.supabase_url)
        self.supabase_anon_key = self._target_value(
            target, "supabase", "anon_key", self.supabase_anon_key
        )
        self.supabase_service_key = self._target_value(
            target,
            "supabase",
            "service_key",
            self.supabase_service_key,
        )
        self.database_url = self._target_value(target, "database", "url", self.database_url)

        missing = [
            name
            for name, value in (
                ("SUPABASE_URL", self.supabase_url),
                ("SUPABASE_ANON_KEY", self.supabase_anon_key),
                ("SUPABASE_SERVICE_KEY", self.supabase_service_key),
            )
            if not value
        ]
        if missing:
            raise ValueError(
                f"Missing required Supabase setting(s) for target '{target}': {', '.join(missing)}."
            )

        return self

    def _target_value(self, target: str, prefix: str, suffix: str, fallback: str) -> str:
        value = getattr(self, f"{prefix}_{target}_{suffix}", "")
        return value or fallback


settings = Settings()  # type: ignore[call-arg]
