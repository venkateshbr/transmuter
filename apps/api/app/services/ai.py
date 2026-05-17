from __future__ import annotations

import asyncio
import re
from typing import Any
from uuid import UUID

from app.agents.portfolio_agent import portfolio_agent
from app.core.database import get_supabase_admin
from app.domain.ai import ChatResponseData, SuggestedPrompt
from app.services.portfolio_rag import PortfolioRAGService


class AIService:
    def __init__(self, tenant_id: UUID):
        self.client = get_supabase_admin()
        self.tenant_id = str(tenant_id)
        self._tenant_uuid = tenant_id
        self._rag = PortfolioRAGService(self.client, tenant_id)

    async def chat(self, query: str) -> ChatResponseData:
        """Chat with Transmuter AI about the portfolio."""
        documents = self._search_with_refresh(query)
        sources = self._rag.citations(documents)
        response = ""
        langfuse_observation = None

        try:
            from app.core.observability import get_langfuse

            langfuse = get_langfuse()
            if langfuse:
                langfuse_observation = langfuse.start_as_current_observation(
                    name="portfolio-chat",
                    input={
                        "query": _mask_pii(query),
                        "retrieved_documents": len(documents),
                    },
                    tags=["ai-chat", "portfolio-rag"],
                )
        except Exception:
            langfuse_observation = None

        try:
            if langfuse_observation:
                with langfuse_observation as observation:
                    response = await self._answer(query, documents)
                    observation.update(
                        output={
                            "response": response,
                            "sources": [source.model_dump() for source in sources],
                        }
                    )
            else:
                response = await self._answer(query, documents)
        except Exception:
            response = self._deterministic_answer(query, documents)

        return ChatResponseData(response=response, sources=sources)

    def suggested_prompts(self) -> list[SuggestedPrompt]:
        return [
            SuggestedPrompt(
                label="At-risk initiatives",
                query="Which initiatives are red or amber, and what risks are driving them?",
            ),
            SuggestedPrompt(
                label="Milestones due soon",
                query="Which portfolio milestones need executive attention this week?",
            ),
            SuggestedPrompt(
                label="Portfolio summary",
                query="Summarize the portfolio with cited initiatives and milestones.",
            ),
        ]

    async def _answer(self, query: str, documents: list[dict[str, Any]]) -> str:
        query_l = query.lower()

        if any(
            phrase in query_l
            for phrase in ("at-risk", "at risk", "summarize the portfolio", "milestones")
        ):
            return self._deterministic_answer(query, documents)

        context = _render_context(documents)
        prompt = (
            f"{_mask_pii(query)}\n\n"
            f"Use only this tenant-scoped context when citing portfolio data:\n{_mask_pii(context)}"
        )
        result = await asyncio.wait_for(
            portfolio_agent.run(prompt, deps=self._tenant_uuid),
            timeout=12.0,
        )
        return str(result.output)

    def _search_with_refresh(self, query: str) -> list[dict[str, Any]]:
        try:
            documents = self._rag.search(query, limit=5)
            if documents:
                return documents
            self._rag.rebuild_index()
            return self._rag.search(query, limit=5)
        except Exception:
            return []

    def _deterministic_answer(
        self,
        query: str,
        documents: list[dict[str, Any]] | None = None,
    ) -> str:
        if documents:
            names = ", ".join(document.get("title", "Untitled") for document in documents[:5])
            return f"Based on the matching portfolio records, the most relevant sources are: {names}."

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


def _render_context(documents: list[dict[str, Any]]) -> str:
    if not documents:
        return "No indexed portfolio documents matched the query."
    lines = []
    for index, document in enumerate(documents, start=1):
        lines.append(
            "[{index}] {source_type}: {title}\n{content}".format(
                index=index,
                source_type=document.get("source_type", "source"),
                title=document.get("title", "Untitled"),
                content=(document.get("content") or "")[:800],
            )
        )
    return "\n\n".join(lines)


def _mask_pii(text: str) -> str:
    masked = re.sub(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+", "[email]", text)
    masked = re.sub(r"\+?\d[\d .()/-]{7,}\d", "[phone]", masked)
    return masked
