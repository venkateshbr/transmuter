"""Nudge delivery helpers for status-update compliance."""

from __future__ import annotations

from dataclasses import dataclass

from app.services.email_delivery import EmailDeliveryService


@dataclass(frozen=True)
class NudgeDeliveryResult:
    status: str
    detail: str | None = None


class NudgeDeliveryService:
    """Delivers owner nudges through configured channels."""

    def __init__(self) -> None:
        self._email = EmailDeliveryService()

    def deliver(
        self,
        *,
        channel: str,
        owner_email: str | None,
        initiative_name: str,
    ) -> NudgeDeliveryResult:
        if channel not in {"email", "both"}:
            return NudgeDeliveryResult(status="sent", detail="in_app")

        if not owner_email:
            return NudgeDeliveryResult(status="queued", detail="owner_email_missing")

        result = self._email.deliver(
            to=[owner_email],
            subject=f"Status update needed: {initiative_name}",
            text=(
                f"{initiative_name} needs a portfolio status update. "
                "Please submit the latest weekly update in Transmuter."
            ),
        )
        return NudgeDeliveryResult(status=result.status, detail=result.detail)
