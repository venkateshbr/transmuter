"""Nudge delivery helpers for status-update compliance."""

from __future__ import annotations

from dataclasses import dataclass

import httpx

from app.core.config import settings


@dataclass(frozen=True)
class NudgeDeliveryResult:
    status: str
    detail: str | None = None


class NudgeDeliveryService:
    """Delivers owner nudges through configured channels."""

    def deliver(
        self,
        *,
        channel: str,
        owner_email: str | None,
        initiative_name: str,
    ) -> NudgeDeliveryResult:
        if channel not in {"email", "both"}:
            return NudgeDeliveryResult(status="sent", detail="in_app")

        if not settings.resend_api_key or not settings.resend_from_email:
            return NudgeDeliveryResult(status="queued", detail="email_not_configured")

        if not owner_email:
            return NudgeDeliveryResult(status="queued", detail="owner_email_missing")

        try:
            response = httpx.post(
                "https://api.resend.com/emails",
                headers={
                    "Authorization": f"Bearer {settings.resend_api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "from": settings.resend_from_email,
                    "to": [owner_email],
                    "subject": f"Status update needed: {initiative_name}",
                    "text": (
                        f"{initiative_name} needs a portfolio status update. "
                        "Please submit the latest weekly update in Transmuter."
                    ),
                },
                timeout=10,
            )
            response.raise_for_status()
        except httpx.HTTPError as exc:
            return NudgeDeliveryResult(status="failed", detail=str(exc))

        return NudgeDeliveryResult(status="sent", detail="email")
