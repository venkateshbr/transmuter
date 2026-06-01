"""Shared email delivery coverage."""

from __future__ import annotations

import httpx

from app.core.config import settings
from app.services.email_delivery import EmailDeliveryService


class FakeResponse:
    def raise_for_status(self) -> None:
        return None


def test_email_delivery_sends_resend_payload_with_normalised_recipients(monkeypatch) -> None:
    captured: dict[str, object] = {}

    def fake_post(_url, *, headers, json, timeout, **_kwargs):  # noqa: ANN001
        captured["headers"] = headers
        captured["json"] = json
        captured["timeout"] = timeout
        return FakeResponse()

    monkeypatch.setattr(settings, "resend_api_key", "re_test_key")
    monkeypatch.setattr(settings, "resend_from_email", "Transmuter <noreply@example.com>")
    monkeypatch.setattr("app.services.email_delivery.httpx.post", fake_post)

    result = EmailDeliveryService().deliver(
        to=["Owner@example.com", " owner@example.com ", "pm@example.com"],
        subject="Minutes",
        text="Meeting minutes",
    )

    assert result.status == "sent"
    assert result.recipient_count == 2
    assert captured["json"] == {
        "from": "Transmuter <noreply@example.com>",
        "to": ["owner@example.com", "pm@example.com"],
        "subject": "Minutes",
        "text": "Meeting minutes",
    }


def test_email_delivery_reports_provider_failure(monkeypatch) -> None:
    def fake_post(_url, **_kwargs):  # noqa: ANN001, ANN003
        raise httpx.ConnectError("provider unavailable")

    monkeypatch.setattr(settings, "resend_api_key", "re_test_key")
    monkeypatch.setattr(settings, "resend_from_email", "Transmuter <noreply@example.com>")
    monkeypatch.setattr("app.services.email_delivery.httpx.post", fake_post)

    result = EmailDeliveryService().deliver(
        to=["owner@example.com"],
        subject="Minutes",
        text="Meeting minutes",
    )

    assert result.status == "failed"
    assert result.recipient_count == 1


def test_email_delivery_queues_when_config_missing(monkeypatch) -> None:
    monkeypatch.setattr(settings, "resend_api_key", "")
    monkeypatch.setattr(settings, "resend_from_email", "")

    result = EmailDeliveryService().deliver(
        to=["owner@example.com"],
        subject="Minutes",
        text="Meeting minutes",
    )

    assert result.status == "queued"
    assert result.detail == "email_not_configured"
