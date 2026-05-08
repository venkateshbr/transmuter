from __future__ import annotations

import asyncio
from typing import Any
from uuid import UUID

from app.agents.portfolio_agent import portfolio_agent
from app.core.database import get_supabase_admin


class AIService:
    def __init__(self, tenant_id: UUID):
        self.client = get_supabase_admin()
        self.tenant_id = str(tenant_id)

    async def chat(self, query: str) -> dict[str, Any]:
        """Chat with Transmuter AI about the portfolio."""
        sources = [
            {"label": "Portfolio initiatives", "source_type": "initiatives"},
            {"label": "Milestones and risks", "source_type": "portfolio"},
        ]
        query_l = query.lower()

        # Fast path for deterministic summary questions
        if any(
            phrase in query_l
            for phrase in ("at-risk", "at risk", "summarize the portfolio", "milestones")
        ):
            return {"response": self._deterministic_answer(query), "sources": sources}

        try:
            from app.core.observability import get_langfuse

            langfuse = get_langfuse()

            if langfuse:
                with langfuse.start_as_current_observation(
                    name="portfolio-chat", input=query, tags=["ai-chat", "portfolio-agent"]
                ) as observation:
                    result = await asyncio.wait_for(
                        portfolio_agent.run(query, deps=UUID(self.tenant_id)),
                        timeout=12.0,
                    )
                    observation.update(output=str(result.output))
                    return {"response": str(result.output), "sources": sources}
            else:
                result = await asyncio.wait_for(
                    portfolio_agent.run(query, deps=UUID(self.tenant_id)),
                    timeout=12.0,
                )
                return {"response": str(result.output), "sources": sources}
        except Exception:
            return {"response": self._deterministic_answer(query), "sources": sources}

    def _deterministic_answer(self, query: str) -> str:
        initiatives = (
            self.client.table("initiatives")
            .select("id, name, rag_status, stage")
            .eq("tenant_id", self.tenant_id)
            .execute()
            .data
            or []
        )
        query_l = query.lower()
        at_risk = [item for item in initiatives if item.get("rag_status") in {"red", "amber"}]

        if any(p in query_l for p in ("risk", "at-risk", "at risk")):
            names = ", ".join(item.get("name", "Unnamed initiative") for item in at_risk[:5])
            return f"{len(at_risk)} initiatives are currently at risk" + (
                f": {names}." if names else "."
            )

        stages: dict[str, int] = {}
        for item in initiatives:
            stage = item.get("stage") or "unknown"
            stages[stage] = stages.get(stage, 0) + 1

        stage_text = ", ".join(
            f"{count} {stage.replace('_', ' ')}" for stage, count in sorted(stages.items())
        )
        return (
            f"The portfolio has {len(initiatives)} initiatives. "
            f"{len(at_risk)} are red or amber. Stage mix: {stage_text or 'no active stages'}."
        )
