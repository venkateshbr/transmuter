"""Shared outbound email delivery helpers."""

from __future__ import annotations

from dataclasses import dataclass

import httpx

from app.core.config import settings


@dataclass(frozen=True)
class EmailDeliveryResult:
    status: str
    detail: str | None = None
    recipient_count: int = 0


class EmailDeliveryService:
    """Delivers application email through the configured Resend account."""

    def deliver(
        self,
        *,
        to: list[str],
        subject: str,
        text: str,
        html: str | None = None,
    ) -> EmailDeliveryResult:
        recipients = self._normalise_recipients(to)
        if not settings.resend_api_key or not settings.resend_from_email:
            return EmailDeliveryResult(
                status="queued",
                detail="email_not_configured",
                recipient_count=len(recipients),
            )

        if not recipients:
            return EmailDeliveryResult(status="queued", detail="recipient_missing")

        payload: dict[str, object] = {
            "from": settings.resend_from_email,
            "to": recipients,
            "subject": subject,
            "text": text,
        }
        if html:
            payload["html"] = html

        try:
            response = httpx.post(
                "https://api.resend.com/emails",
                headers={
                    "Authorization": f"Bearer {settings.resend_api_key}",
                    "Content-Type": "application/json",
                },
                json=payload,
                timeout=10,
            )
            response.raise_for_status()
        except httpx.HTTPError as exc:
            return EmailDeliveryResult(
                status="failed",
                detail=str(exc),
                recipient_count=len(recipients),
            )

        return EmailDeliveryResult(status="sent", detail="email", recipient_count=len(recipients))

    @staticmethod
    def _normalise_recipients(recipients: list[str]) -> list[str]:
        seen: set[str] = set()
        normalised: list[str] = []
        for recipient in recipients:
            email = recipient.strip().lower()
            if not email or email in seen:
                continue
            seen.add(email)
            normalised.append(email)
        return normalised
