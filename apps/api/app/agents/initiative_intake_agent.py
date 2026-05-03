"""PydanticAI initiative intake agent with deterministic fallback.

The agent contract lives here so the platform can evolve to external LLM-backed
suggestions without blocking core creation when OpenRouter/Langfuse are absent.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from uuid import uuid4

from langfuse import Langfuse
from langfuse.types import TraceContext
from openai import AsyncOpenAI
from pydantic_ai import Agent
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openai import OpenAIProvider

from app.core.config import settings
from app.domain.initiative_intake import (
    InitiativeIntakeRequest,
    InitiativeIntakeSuggestions,
    SuggestedCostLine,
    SuggestedFinancialEntry,
    SuggestedKPI,
    SuggestedMilestone,
    SuggestedRisk,
)
from app.domain.kpis import KPIEntryUpsert


initiative_intake_agent: Agent[None, InitiativeIntakeSuggestions] | None = None
langfuse_client: Langfuse | None = None


def _get_agent() -> Agent[None, InitiativeIntakeSuggestions]:
    global initiative_intake_agent
    if initiative_intake_agent is None:
        client = AsyncOpenAI(
            base_url=settings.openrouter_base_url,
            api_key=settings.openrouter_api_key,
        )
        provider = OpenAIProvider(openai_client=client)
        model = OpenAIChatModel(settings.default_model, provider=provider)
        initiative_intake_agent = Agent(
            model,
            output_type=InitiativeIntakeSuggestions,
            system_prompt=(
                "You are Transmuter's initiative intake analyst. Generate structured, "
                "reviewable financial, KPI, risk, and milestone suggestions. Never include "
                "PII in external prompts; rely only on business context provided by the user."
            ),
        )
    return initiative_intake_agent


def _get_langfuse() -> Langfuse | None:
    global langfuse_client
    if not (
        settings.ai_enabled
        and settings.langfuse_public_key
        and settings.langfuse_secret_key
    ):
        return None
    if langfuse_client is None:
        langfuse_client = Langfuse(
            public_key=settings.langfuse_public_key,
            secret_key=settings.langfuse_secret_key,
            host=settings.langfuse_host,
            timeout=5,
        )
    return langfuse_client


async def generate_intake_suggestions(
    request: InitiativeIntakeRequest,
) -> InitiativeIntakeSuggestions:
    """Generate suggestions, falling back deterministically if LLM access is unavailable."""
    trace_id = _trace_id()
    prompt = _masked_prompt(request)
    if settings.ai_enabled and settings.openrouter_api_key:
        try:
            langfuse = _get_langfuse()
            if langfuse:
                with langfuse.start_as_current_observation(
                    name="initiative_intake",
                    as_type="agent",
                    trace_context=TraceContext(trace_id=trace_id),
                    input=prompt,
                    metadata={"source": "new_initiative"},
                    model=settings.default_model,
                ):
                    result = await _get_agent().run(prompt)
                    suggestions = _with_trace(result.output, trace_id, langfuse)
                    suggestions.agent_status = "generated"
                    langfuse.update_current_span(
                        output=suggestions.model_dump(mode="json"),
                    )
                    langfuse.flush()
                    return suggestions
            result = await _get_agent().run(prompt)
            suggestions = _with_trace(result.output, trace_id, None)
            suggestions.agent_status = "generated"
            return suggestions
        except Exception:
            # Core creation must not depend on external AI availability.
            pass
    return deterministic_intake_suggestions(request, trace_id=trace_id)


def deterministic_intake_suggestions(
    request: InitiativeIntakeRequest,
    trace_id: str | None = None,
) -> InitiativeIntakeSuggestions:
    init = request.initiative
    name = init.name
    start_year = init.planned_start.year if init.planned_start else date.today().year
    is_cost = init.type in {"cost_reduction", "cost_avoidance"}
    base_value = Decimal("75000.0000") if is_cost else Decimal("125000.0000")
    high_value = Decimal("115000.0000") if is_cost else Decimal("190000.0000")

    return InitiativeIntakeSuggestions(
        trace_id=trace_id or f"deterministic-intake-{uuid4()}",
        trace_url=_trace_url(trace_id),
        agent_status="deterministic_fallback",
        financial_entries=[
            SuggestedFinancialEntry(
                year=start_year,
                quarter=1,
                revenue_uplift_base=Decimal("0") if is_cost else base_value,
                revenue_uplift_high=Decimal("0") if is_cost else high_value,
                gross_margin_base=base_value,
                gross_margin_high=high_value,
                gm_uplift_base=base_value,
                gm_uplift_high=high_value,
            )
        ],
        cost_lines=[
            SuggestedCostLine(
                name="Implementation and change support",
                year=start_year,
                quarter=1,
                amount_plan=Decimal("15000.0000"),
                is_recurring=False,
            )
        ],
        kpis=[
            SuggestedKPI(
                name="Cycle time reduction",
                type="operational",
                frequency="quarterly",
                unit="%",
                entries=[
                    KPIEntryUpsert(
                        year=start_year,
                        quarter=1,
                        value_base="15.0000",
                        value_high="25.0000",
                    )
                ],
            ),
            SuggestedKPI(
                name="Adoption rate",
                type="operational",
                frequency="quarterly",
                unit="%",
                entries=[
                    KPIEntryUpsert(
                        year=start_year,
                        quarter=1,
                        value_base="70.0000",
                        value_high="90.0000",
                    )
                ],
            ),
            SuggestedKPI(
                name="Value delivered",
                type="custom",
                frequency="quarterly",
                unit="USD",
                entries=[
                    KPIEntryUpsert(
                        year=start_year,
                        quarter=1,
                        value_base=str(base_value),
                        value_high=str(high_value),
                    )
                ],
            ),
        ],
        risks=[
            SuggestedRisk(
                description=f"Stakeholder adoption may slow {name}",
                type="people",
                impact="medium",
                likelihood="medium",
                mitigation="Confirm owner cadence, adoption metrics, and change champions.",
            ),
            SuggestedRisk(
                description="Source data quality may delay benefits tracking",
                type="technology",
                impact="high",
                likelihood="medium",
                mitigation="Validate baseline data and assign remediation owners before launch.",
            ),
            SuggestedRisk(
                description="Benefits may not convert into run-rate savings",
                type="financial",
                impact="medium",
                likelihood="medium",
                mitigation="Tie value tracking to Finance sign-off and monthly value bridge review.",
            ),
        ],
        milestones=[
            SuggestedMilestone(
                name="Scope and baseline signed off",
                description="Confirm scope, baseline, and value logic.",
                priority="high",
                planned_start=_iso(init.planned_start),
                planned_end=_iso(init.planned_start),
            ),
            SuggestedMilestone(
                name="Pilot completed",
                description="Run a controlled pilot and record lessons.",
                priority="medium",
                planned_start=_iso(init.planned_start),
                planned_end=_iso(init.planned_end),
            ),
            SuggestedMilestone(
                name="Benefits tracking live",
                description="Operationalize KPI and financial tracking.",
                priority="high",
                planned_start=_iso(init.planned_start),
                planned_end=_iso(init.planned_end),
            ),
        ],
    )


def _masked_prompt(request: InitiativeIntakeRequest) -> str:
    init = request.initiative
    return (
        f"Initiative name: {init.name}\n"
        f"Type: {init.type}\n"
        f"Impact type: {init.impact_type}\n"
        f"Theme: {init.theme}\n"
        f"Country/market: {init.country}\n"
        f"Priority: {init.priority}\n"
        f"Summary: {init.summary}\n"
        f"Value logic: {init.value_logic}\n"
        f"Dependencies: {init.dependencies_text}\n"
        f"Timeline: {init.planned_start} to {init.planned_end}\n"
        "Generate only structured suggestions for HITL review."
    )


def _iso(value: date | None) -> str | None:
    return value.isoformat() if value else None


def _trace_id() -> str:
    langfuse = _get_langfuse()
    if langfuse:
        return langfuse.create_trace_id(seed=f"initiative-intake-{uuid4()}")
    return f"deterministic-intake-{uuid4()}"


def _trace_url(trace_id: str | None) -> str | None:
    langfuse = _get_langfuse()
    if langfuse and trace_id:
        return langfuse.get_trace_url(trace_id=trace_id)
    return None


def _with_trace(
    suggestions: InitiativeIntakeSuggestions,
    trace_id: str,
    langfuse: Langfuse | None,
) -> InitiativeIntakeSuggestions:
    suggestions.trace_id = trace_id
    suggestions.trace_url = (
        langfuse.get_trace_url(trace_id=trace_id) if langfuse else None
    )
    return suggestions
