"""HTTP client for the private Hermes Responses-compatible API."""

from __future__ import annotations

import asyncio
import random
from typing import Any

import httpx

_RETRYABLE_STATUS = {429, 502, 503, 504}
_RETRYABLE_ERRORS = (
    httpx.ConnectError,
    httpx.ConnectTimeout,
    httpx.ReadTimeout,
    httpx.PoolTimeout,
    httpx.RemoteProtocolError,
)


class HermesClient:
    def __init__(
        self,
        *,
        base_url: str,
        api_key: str,
        timeout_seconds: float = 45.0,
        max_retries: int = 2,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.timeout_seconds = timeout_seconds
        self.max_retries = max(0, max_retries)

    async def create_response(
        self,
        *,
        input_text: str,
        conversation: str,
        instructions: str,
        model: str,
    ) -> dict[str, Any]:
        payload = {
            "model": model,
            "input": input_text,
            "conversation": conversation,
            "instructions": instructions,
            "store": True,
            "stream": False,
        }
        headers = {"Authorization": f"Bearer {self.api_key}"} if self.api_key else {}
        timeout = httpx.Timeout(self.timeout_seconds, connect=5.0, write=10.0, pool=5.0)
        last_error: Exception | None = None
        for attempt in range(self.max_retries + 1):
            try:
                async with httpx.AsyncClient(
                    base_url=self.base_url,
                    headers=headers,
                    timeout=timeout,
                ) as client:
                    response = await client.post("/v1/responses", json=payload)
                    response.raise_for_status()
                    data = response.json()
                    if not isinstance(data, dict):
                        raise ValueError("Hermes returned an invalid response")
                    return data
            except httpx.HTTPStatusError as exc:
                last_error = exc
                if exc.response.status_code not in _RETRYABLE_STATUS:
                    raise
            except _RETRYABLE_ERRORS as exc:
                last_error = exc
            if attempt < self.max_retries:
                await asyncio.sleep(random.uniform(0.0, min(2.0, 0.25 * (2**attempt))))
        if last_error is None:
            raise RuntimeError("Hermes request failed")
        raise last_error


def extract_hermes_text(payload: dict[str, Any]) -> str:
    chunks: list[str] = []
    for item in payload.get("output") or []:
        if not isinstance(item, dict) or item.get("type") != "message":
            continue
        for part in item.get("content") or []:
            if isinstance(part, dict) and part.get("type") == "output_text":
                text = part.get("text")
                if isinstance(text, str):
                    chunks.append(text)
    return "".join(chunks).strip()
