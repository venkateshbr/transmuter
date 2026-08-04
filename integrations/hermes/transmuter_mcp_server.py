"""MCP bridge from Hermes to the private Transmuter AI tool broker."""

from __future__ import annotations

import os
from typing import Any

import httpx
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("transmuter")
_DEFAULT_BASE_URL = "http://api:8001"
_EXECUTE_PATH = "/ai-tools/execute"


@mcp.tool()
async def transmuter_portfolio_overview(context_ref: str) -> dict[str, Any]:
    """Read aggregate initiative, risk, milestone, action, and KPI health."""
    return await _execute("transmuter.portfolio.overview", context_ref, {})


@mcp.tool()
async def transmuter_portfolio_initiatives(
    context_ref: str,
    search: str | None = None,
    rag_status: str | None = None,
    stage: str | None = None,
    limit: int = 25,
) -> dict[str, Any]:
    """Read a filtered, PII-safe initiative pack from Transmuter."""
    return await _execute(
        "transmuter.portfolio.initiatives",
        context_ref,
        _optional_args(
            {"search": search, "rag_status": rag_status, "stage": stage, "limit": limit}
        ),
    )


@mcp.tool()
async def transmuter_governance_read_pack(context_ref: str) -> dict[str, Any]:
    """Read aggregate milestone and risk governance health."""
    return await _execute("transmuter.governance.read_pack", context_ref, {})


@mcp.tool()
async def transmuter_financials_read_pack(
    context_ref: str,
    year: int | None = None,
) -> dict[str, Any]:
    """Read Decimal-safe portfolio financial totals, optionally for one year."""
    return await _execute(
        "transmuter.financials.read_pack",
        context_ref,
        _optional_args({"year": year}),
    )


@mcp.tool()
async def transmuter_tools_catalog(context_ref: str) -> dict[str, Any]:
    """Read the user-facing catalog of built-in Transmuter AI capabilities."""
    return await _execute("transmuter.tools.catalog", context_ref, {})


async def _execute(
    tool_name: str,
    context_ref: str,
    arguments: dict[str, Any],
) -> dict[str, Any]:
    token = os.getenv("HERMES_TOOL_TOKEN", "").strip()
    if not token:
        raise RuntimeError("Transmuter tool broker token is not configured")
    base_url = os.getenv("TRANSMUTER_INTERNAL_API_URL", _DEFAULT_BASE_URL).rstrip("/")
    timeout = float(os.getenv("TRANSMUTER_TOOL_TIMEOUT_SECONDS", "30"))
    try:
        async with httpx.AsyncClient(base_url=base_url, timeout=timeout) as client:
            response = await client.post(
                _EXECUTE_PATH,
                json={
                    "context_ref": context_ref,
                    "tool_name": tool_name,
                    "arguments": arguments,
                },
                headers={"Authorization": f"Bearer {token}"},
            )
            response.raise_for_status()
            data = response.json()
    except httpx.HTTPStatusError as exc:
        raise RuntimeError(
            f"Transmuter tool broker rejected the request with HTTP {exc.response.status_code}"
        ) from exc
    except httpx.HTTPError as exc:
        raise RuntimeError("Transmuter tool broker request failed") from exc
    result = data.get("result")
    return result if isinstance(result, dict) else {"result": result}


def _optional_args(arguments: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in arguments.items() if value is not None}


if __name__ == "__main__":
    mcp.run()
