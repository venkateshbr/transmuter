from __future__ import annotations

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from supabase import Client

MICROSOFT_GRAPH_PROVIDER = "microsoft_graph"


class MeetingIntegrationRepository:
    def __init__(self, client: Client, tenant_id: UUID) -> None:
        self._client = client
        self._tenant_id = str(tenant_id)

    def list_connections(self) -> list[dict[str, Any]]:
        result = (
            self._client.table("integration_connections")
            .select(
                "id,tenant_id,provider,organizer_email,external_account_id,"
                "token_expires_at,scopes,sync_status,sync_error,last_synced_at,"
                "created_at,updated_at,deployment_environment,deployment_schema,"
                "entra_tenant_id,oauth_client_id,oauth_redirect_uri,"
                "context_fingerprint,oauth_generation,token_generation,connected_by_user_id"
            )
            .eq("tenant_id", self._tenant_id)
            .execute()
        )
        return list(result.data or [])

    def create_oauth_state(self, data: dict[str, Any]) -> dict[str, Any]:
        result = self._client.rpc(
            "create_microsoft_graph_oauth_state",
            {
                "p_tenant_id": self._tenant_id,
                "p_provider": MICROSOFT_GRAPH_PROVIDER,
                "p_state_digest": data["state_digest"],
                "p_browser_binding_digest": data["browser_binding_digest"],
                "p_initiated_by_user_id": data["initiated_by_user_id"],
                "p_pkce_verifier_encrypted": data["pkce_verifier_encrypted"],
                "p_nonce_digest": data["nonce_digest"],
                "p_deployment_environment": data["deployment_environment"],
                "p_deployment_schema": data["deployment_schema"],
                "p_entra_tenant_id": data["entra_tenant_id"],
                "p_oauth_client_id": data["oauth_client_id"],
                "p_oauth_redirect_uri": data["oauth_redirect_uri"],
                "p_encryption_key_fingerprint": data["encryption_key_fingerprint"],
                "p_context_fingerprint": data["context_fingerprint"],
                "p_authorization_scopes": data["authorization_scopes"],
                "p_required_api_scopes": data["required_api_scopes"],
            },
        ).execute()
        state_id = self._scalar_rpc_value(result.data, "state_id")
        if not state_id:
            raise RuntimeError("Microsoft Graph OAuth state was not created")
        return {"id": str(state_id)}

    def purge_expired_oauth_states(
        self,
        *,
        expired_before: datetime,
    ) -> None:
        (
            self._client.table("integration_oauth_states")
            .delete()
            .eq("tenant_id", self._tenant_id)
            .eq("provider", MICROSOFT_GRAPH_PROVIDER)
            .lt("expires_at", expired_before.isoformat())
            .execute()
        )

    def consume_oauth_state(
        self,
        *,
        state_digest: str,
        browser_binding_digest: str,
        context_fingerprint: str,
        consumed_at: datetime,
        terminal: Literal["cancelled", "failed"] | None = None,
        failure_code: str | None = None,
    ) -> dict[str, Any] | None:
        now_value = consumed_at.isoformat()
        updates: dict[str, Any] = {"consumed_at": now_value}
        if terminal is not None:
            updates[f"{terminal}_at"] = now_value
            updates["failure_code"] = failure_code
            updates["pkce_verifier_encrypted"] = None

        result = (
            self._client.table("integration_oauth_states")
            .update(updates)
            .eq("tenant_id", self._tenant_id)
            .eq("provider", MICROSOFT_GRAPH_PROVIDER)
            .eq("state_digest", state_digest)
            .eq("browser_binding_digest", browser_binding_digest)
            .eq("context_fingerprint", context_fingerprint)
            .is_("consumed_at", "null")
            .is_("cancelled_at", "null")
            .is_("failed_at", "null")
            .is_("completed_at", "null")
            .gt("expires_at", now_value)
            .execute()
        )
        if not result.data:
            return None
        return dict(result.data[0])

    def fail_oauth_state(
        self,
        *,
        state_digest: str,
        context_fingerprint: str,
        failed_at: datetime,
        failure_code: str,
    ) -> bool:
        now_value = failed_at.isoformat()
        result = (
            self._client.table("integration_oauth_states")
            .update(
                {
                    "failed_at": now_value,
                    "failure_code": failure_code,
                    "pkce_verifier_encrypted": None,
                }
            )
            .eq("tenant_id", self._tenant_id)
            .eq("provider", MICROSOFT_GRAPH_PROVIDER)
            .eq("state_digest", state_digest)
            .eq("context_fingerprint", context_fingerprint)
            .is_("cancelled_at", "null")
            .is_("failed_at", "null")
            .is_("completed_at", "null")
            .execute()
        )
        return bool(result.data)

    def get_actor(self, user_id: str) -> dict[str, Any] | None:
        result = (
            self._client.table("users")
            .select("id,tenant_id,role,status,must_change_password")
            .eq("tenant_id", self._tenant_id)
            .eq("id", user_id)
            .maybe_single()
            .execute()
        )
        if not result or not result.data:
            return None
        return dict(result.data)

    def complete_microsoft_graph_oauth(
        self,
        *,
        state_digest: str,
        context_fingerprint: str,
        external_account_id: str,
        organizer_email: str,
        access_token_encrypted: str,
        refresh_token_encrypted: str,
        token_expires_at: datetime,
        scopes: tuple[str, ...],
    ) -> str:
        result = self._client.rpc(
            "complete_microsoft_graph_oauth",
            {
                "p_tenant_id": self._tenant_id,
                "p_provider": MICROSOFT_GRAPH_PROVIDER,
                "p_state_digest": state_digest,
                "p_context_fingerprint": context_fingerprint,
                "p_external_account_id": external_account_id,
                "p_organizer_email": organizer_email,
                "p_access_token_encrypted": access_token_encrypted,
                "p_refresh_token_encrypted": refresh_token_encrypted,
                "p_token_expires_at": token_expires_at.isoformat(),
                "p_scopes": list(scopes),
            },
        ).execute()
        connection_id = self._scalar_rpc_value(result.data, "connection_id")
        if not connection_id:
            raise RuntimeError("Microsoft Graph connection was not completed")
        return str(connection_id)

    def disconnect_microsoft_graph_connection(
        self,
        connection_id: UUID,
        actor_id: UUID,
    ) -> bool:
        result = self._client.rpc(
            "disconnect_microsoft_graph_connection",
            {
                "p_tenant_id": self._tenant_id,
                "p_provider": MICROSOFT_GRAPH_PROVIDER,
                "p_connection_id": str(connection_id),
                "p_actor_id": str(actor_id),
            },
        ).execute()
        value = self._scalar_rpc_value(result.data, "disconnected")
        return value is True

    @staticmethod
    def _scalar_rpc_value(data: Any, key: str) -> Any:
        if isinstance(data, list):
            if not data:
                return None
            value = data[0]
        else:
            value = data
        if isinstance(value, dict):
            if key in value:
                return value[key]
            if len(value) == 1:
                return next(iter(value.values()))
            return None
        return value
