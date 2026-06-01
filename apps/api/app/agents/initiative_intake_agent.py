"""PydanticAI initiative intake agent with deterministic fallback.

The agent contract lives here so the platform can evolve to external LLM-backed
suggestions without blocking core creation when OpenRouter/Langfuse are absent.
"""

from __future__ import annotations

import asyncio
import re
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
from app.core.observability import record_agent_run, start_agent_timer
from app.domain.initiative_intake import (
    InitiativeDraft,
    InitiativeFieldExtractionResult,
    InitiativeIntakeRequest,
    InitiativeIntakeSuggestions,
    KPISuggestion,
    KPISuggestionResult,
    RiskPattern,
    RiskPatternScanResult,
    SuggestedCostLine,
    SuggestedFinancialEntry,
    SuggestedKPI,
    SuggestedMilestone,
    SuggestedRisk,
)
from app.domain.kpis import KPIEntryUpsert

initiative_intake_agent: Agent[None, InitiativeIntakeSuggestions] | None = None
initiative_field_agent: Agent[None, InitiativeFieldExtractionResult] | None = None
langfuse_client: Langfuse | None = None
INTAKE_AGENT_TIMEOUT_SECONDS = 8


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


def _get_field_agent() -> Agent[None, InitiativeFieldExtractionResult]:
    global initiative_field_agent
    if initiative_field_agent is None:
        client = AsyncOpenAI(
            base_url=settings.openrouter_base_url,
            api_key=settings.openrouter_api_key,
        )
        provider = OpenAIProvider(openai_client=client)
        model = OpenAIChatModel(settings.default_model, provider=provider)
        initiative_field_agent = Agent(
            model,
            output_type=InitiativeFieldExtractionResult,
            system_prompt=(
                "You extract initiative intake fields for Transmuter. Return typed JSON only. "
                "Use null when evidence is absent. Never invent names, dates, countries, "
                "workstreams, value logic, dependencies, or priority."
            ),
        )
    return initiative_field_agent


def _get_langfuse() -> Langfuse | None:
    global langfuse_client
    if not (settings.ai_enabled and settings.langfuse_public_key and settings.langfuse_secret_key):
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
    started_at = start_agent_timer()
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
                    result = await asyncio.wait_for(
                        _get_agent().run(prompt),
                        timeout=INTAKE_AGENT_TIMEOUT_SECONDS,
                    )
                    suggestions = _with_trace(result.output, trace_id, langfuse)
                    suggestions.agent_status = "generated"
                    langfuse.update_current_span(
                        output=suggestions.model_dump(mode="json"),
                    )
                    langfuse.flush()
                    record_agent_run("initiative_intake", "unscoped", "generated", started_at)
                    return suggestions
            result = await asyncio.wait_for(
                _get_agent().run(prompt),
                timeout=INTAKE_AGENT_TIMEOUT_SECONDS,
            )
            suggestions = _with_trace(result.output, trace_id, None)
            suggestions.agent_status = "generated"
            record_agent_run("initiative_intake", "unscoped", "generated", started_at)
            return suggestions
        except Exception:
            # Core creation must not depend on external AI availability.
            pass
    suggestions = deterministic_intake_suggestions(request, trace_id=trace_id)
    record_agent_run("initiative_intake", "unscoped", suggestions.agent_status, started_at)
    return suggestions


async def extract_initiative_fields(text: str) -> InitiativeFieldExtractionResult:
    """Extract a structured initiative draft from raw text with safe fallback."""
    trace_id = _trace_id()
    prompt = _masked_free_text(text)
    input_tokens = _estimate_tokens(prompt)
    fallback = deterministic_field_extraction(prompt, trace_id=trace_id)
    if settings.ai_enabled and settings.openrouter_api_key:
        try:
            langfuse = _get_langfuse()
            if langfuse:
                with langfuse.start_as_current_observation(
                    name="initiative_field_extraction",
                    as_type="agent",
                    trace_context=TraceContext(trace_id=trace_id),
                    input=prompt,
                    metadata={"input_tokens": input_tokens},
                    model=settings.default_model,
                ):
                    result = await asyncio.wait_for(
                        _get_field_agent().run(_field_prompt(prompt)),
                        timeout=INTAKE_AGENT_TIMEOUT_SECONDS,
                    )
                    extracted = _with_field_trace(
                        result.output,
                        trace_id=trace_id,
                        langfuse=langfuse,
                        input_tokens=input_tokens,
                    )
                    _fill_missing_draft_fields(extracted.draft, fallback.draft)
                    extracted.agent_status = "generated"
                    langfuse.update_current_span(
                        output=extracted.model_dump(mode="json"),
                        metadata={
                            "input_tokens": extracted.input_tokens,
                            "output_tokens": extracted.output_tokens,
                            "confidence": extracted.confidence,
                        },
                    )
                    langfuse.flush()
                    return extracted
            result = await asyncio.wait_for(
                _get_field_agent().run(_field_prompt(prompt)),
                timeout=INTAKE_AGENT_TIMEOUT_SECONDS,
            )
            extracted = _with_field_trace(
                result.output,
                trace_id=trace_id,
                langfuse=None,
                input_tokens=input_tokens,
            )
            _fill_missing_draft_fields(extracted.draft, fallback.draft)
            extracted.agent_status = "generated"
            return extracted
        except Exception:
            pass
    return fallback


def deterministic_intake_suggestions(
    request: InitiativeIntakeRequest,
    trace_id: str | None = None,
) -> InitiativeIntakeSuggestions:
    init = request.initiative
    start_year = init.planned_start.year if init.planned_start else date.today().year
    is_cost = init.type in {"cost_reduction", "cost_avoidance"}
    base_value = Decimal("75000.0000") if is_cost else Decimal("125000.0000")
    high_value = Decimal("115000.0000") if is_cost else Decimal("190000.0000")
    kpi_result = suggest_kpis(init.type, init.name, init.value_logic)
    risk_result = scan_risk_patterns(
        InitiativeDraft(
            name=init.name,
            type=init.type,
            priority=init.priority,
            country=init.country,
            summary=init.summary,
            value_logic=init.value_logic,
            planned_end=init.planned_end,
            dependencies=init.dependencies_text,
        )
    )

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
                name=kpi.name,
                type=kpi.type,
                category=kpi.category,
                frequency=kpi.frequency,
                unit=kpi.unit,
                entries=[
                    KPIEntryUpsert(
                        year=start_year,
                        quarter=1,
                        value_base="70.0000" if kpi.unit == "%" else str(base_value),
                        value_high="90.0000" if kpi.unit == "%" else str(high_value),
                    )
                ],
            )
            for kpi in kpi_result.suggestions
        ],
        risks=[
            SuggestedRisk(
                description=risk.description,
                type=risk.type,
                impact=risk.impact,
                likelihood=risk.likelihood,
                mitigation=risk.mitigation,
            )
            for risk in risk_result.risks
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


def suggest_kpis(
    initiative_type: str | None,
    initiative_name: str | None,
    value_logic: str | None,
) -> KPISuggestionResult:
    """Suggest domain-relevant KPI candidates for HITL review."""
    name = initiative_name or "the initiative"
    value_text = (value_logic or "").lower()
    return KPISuggestionResult(
        suggestions=[
            KPISuggestion(
                name=pattern["name"],
                type=pattern["type"],  # type: ignore[arg-type]
                category=pattern["category"],
                frequency=pattern["frequency"],  # type: ignore[arg-type]
                unit=pattern["unit"],
                rationale=pattern["rationale"].format(name=name),
            )
            for pattern in _kpi_patterns_for_type(initiative_type, value_text)[:5]
        ]
    )


def scan_risk_patterns(initiative_draft: InitiativeDraft) -> RiskPatternScanResult:
    """Return pre-populated risk patterns based on initiative type and draft fields."""
    name = initiative_draft.name or "this initiative"
    risks = [
        RiskPattern(
            description=pattern["description"].format(name=name),
            type=pattern["type"],  # type: ignore[arg-type]
            impact=pattern["impact"],  # type: ignore[arg-type]
            likelihood=pattern["likelihood"],  # type: ignore[arg-type]
            mitigation=pattern["mitigation"],
            rationale=pattern["rationale"],
        )
        for pattern in _risk_patterns_for_type(initiative_draft.type)[:4]
    ]
    if initiative_draft.dependencies and not any(item.type == "operational" for item in risks):
        risks.append(
            RiskPattern(
                description=f"Dependency readiness may delay {name}",
                type="operational",
                impact="medium",
                likelihood="medium",
                mitigation="Convert each dependency into an owned milestone with weekly review.",
                rationale="The intake text names dependencies, so delivery risk should be tracked.",
            )
        )
    return RiskPatternScanResult(risks=risks[:4])


def deterministic_field_extraction(
    text: str,
    trace_id: str | None = None,
) -> InitiativeFieldExtractionResult:
    """Conservative local extraction used when LLM access is unavailable."""
    clean = _collapse(_masked_free_text(text))
    lowered = clean.lower()
    draft = InitiativeDraft(
        name=_extract_name(clean),
        type=_extract_type(lowered),  # type: ignore[arg-type]
        priority=_extract_priority(lowered),  # type: ignore[arg-type]
        workstream=_extract_labeled_text(clean, ("workstream", "stream")),
        country=_extract_labeled_text(clean, ("country", "market", "region")),
        summary=_extract_summary(clean),
        value_logic=_extract_labeled_text(clean, ("value logic", "benefit", "benefits")),
        planned_end=_extract_date(clean),
        dependencies=_extract_labeled_text(clean, ("dependencies", "dependency", "depends on")),
    )
    fields = draft.model_dump()
    extracted_count = sum(1 for value in fields.values() if value is not None)
    confidence = min(0.95, 0.15 + (extracted_count / len(fields)) * 0.8)
    return InitiativeFieldExtractionResult(
        trace_id=trace_id or f"deterministic-field-{uuid4()}",
        trace_url=_trace_url(trace_id),
        agent_status="deterministic_fallback",
        confidence=round(confidence, 2),
        input_tokens=_estimate_tokens(clean),
        output_tokens=_estimate_tokens(draft.model_dump_json(exclude_none=True)),
        draft=draft,
    )


def _kpi_patterns_for_type(
    initiative_type: str | None,
    value_logic: str,
) -> list[dict[str, str]]:
    common = [
        {
            "name": "Value delivered",
            "type": "custom",
            "category": "financial",
            "frequency": "quarterly",
            "unit": "USD",
            "rationale": "Tracks whether {name} is converting planned value into measurable delivery.",
        },
        {
            "name": "Adoption rate",
            "type": "operational",
            "category": "adoption",
            "frequency": "quarterly",
            "unit": "%",
            "rationale": "Adoption is an early indicator that {name} will sustain benefits.",
        },
    ]
    by_type: dict[str, list[dict[str, str]]] = {
        "revenue_growth": [
            {
                "name": "Incremental gross margin",
                "type": "gross_margin",
                "category": "financial",
                "frequency": "quarterly",
                "unit": "USD",
                "rationale": "Revenue initiatives should prove contribution after margin, not just bookings.",
            },
            {
                "name": "Qualified pipeline created",
                "type": "custom",
                "category": "commercial",
                "frequency": "monthly",
                "unit": "USD",
                "rationale": "Pipeline is the leading indicator for {name}'s revenue conversion.",
            },
            {
                "name": "Win rate uplift",
                "type": "operational",
                "category": "commercial",
                "frequency": "quarterly",
                "unit": "%",
                "rationale": "Win-rate movement validates whether the commercial intervention is working.",
            },
        ],
        "cost_reduction": [
            {
                "name": "Run-rate savings realized",
                "type": "custom",
                "category": "financial",
                "frequency": "quarterly",
                "unit": "USD",
                "rationale": "Cost-reduction work must show savings flowing into the run-rate baseline.",
            },
            {
                "name": "Cycle time reduction",
                "type": "operational",
                "category": "productivity",
                "frequency": "quarterly",
                "unit": "%",
                "rationale": "Cycle-time movement links {name} to operational efficiency.",
            },
            {
                "name": "Cost per transaction",
                "type": "operational",
                "category": "unit economics",
                "frequency": "monthly",
                "unit": "USD",
                "rationale": "Unit cost shows whether savings scale with transaction volume.",
            },
        ],
        "cost_avoidance": [
            {
                "name": "Avoided spend validated",
                "type": "custom",
                "category": "financial",
                "frequency": "quarterly",
                "unit": "USD",
                "rationale": "Cost-avoidance initiatives need a Finance-validated avoided-spend baseline.",
            },
            {
                "name": "Demand deflection rate",
                "type": "operational",
                "category": "control",
                "frequency": "quarterly",
                "unit": "%",
                "rationale": "Deflection confirms {name} is preventing future cost growth.",
            },
            {
                "name": "Forecast variance avoided",
                "type": "custom",
                "category": "forecast",
                "frequency": "quarterly",
                "unit": "%",
                "rationale": "Variance avoided shows whether exposure is being controlled.",
            },
        ],
        "compliance": [
            {
                "name": "Open findings reduced",
                "type": "operational",
                "category": "compliance",
                "frequency": "monthly",
                "unit": "count",
                "rationale": "Compliance work should reduce unresolved findings, not only complete tasks.",
            },
            {
                "name": "Control effectiveness pass rate",
                "type": "operational",
                "category": "control",
                "frequency": "quarterly",
                "unit": "%",
                "rationale": "Pass rate confirms controls embedded by {name} operate as designed.",
            },
            {
                "name": "Regulatory deadline adherence",
                "type": "operational",
                "category": "compliance",
                "frequency": "monthly",
                "unit": "%",
                "rationale": "Deadline adherence is a direct success measure for compliance initiatives.",
            },
        ],
        "capability_building": [
            {
                "name": "Capability adoption rate",
                "type": "operational",
                "category": "adoption",
                "frequency": "quarterly",
                "unit": "%",
                "rationale": "Capability work must demonstrate that teams are using the new practice.",
            },
            {
                "name": "Practitioner proficiency score",
                "type": "custom",
                "category": "capability",
                "frequency": "quarterly",
                "unit": "%",
                "rationale": "Proficiency validates whether {name} is changing skill depth.",
            },
            {
                "name": "Process adherence rate",
                "type": "operational",
                "category": "governance",
                "frequency": "monthly",
                "unit": "%",
                "rationale": "Adherence shows whether the capability is embedded in the operating rhythm.",
            },
        ],
    }
    selected = by_type.get(initiative_type or "", [])
    if "margin" in value_logic:
        selected = [
            {
                "name": "Gross margin uplift",
                "type": "gross_margin",
                "category": "financial",
                "frequency": "quarterly",
                "unit": "USD",
                "rationale": "The value logic references margin, so gross margin uplift should be tracked.",
            },
            *selected,
        ]
    return [*selected, *common]


def _risk_patterns_for_type(initiative_type: str | None) -> list[dict[str, str]]:
    common = [
        {
            "description": "Benefits may not convert into run-rate value for {name}",
            "type": "financial",
            "impact": "medium",
            "likelihood": "medium",
            "mitigation": "Tie value tracking to Finance sign-off and monthly value bridge review.",
            "rationale": "Every transformation initiative needs benefit-realization control.",
        },
        {
            "description": "Stakeholder adoption may slow {name}",
            "type": "people",
            "impact": "medium",
            "likelihood": "medium",
            "mitigation": "Confirm owner cadence, adoption metrics, and change champions.",
            "rationale": "Adoption risk is common when operating routines change.",
        },
    ]
    by_type: dict[str, list[dict[str, str]]] = {
        "revenue_growth": [
            {
                "description": "Pipeline quality may not support forecast revenue for {name}",
                "type": "financial",
                "impact": "high",
                "likelihood": "medium",
                "mitigation": "Review pipeline quality, win-rate assumptions, and margin thresholds monthly.",
                "rationale": "Commercial initiatives often overstate pipeline conversion.",
            },
            {
                "description": "Sales adoption may lag the new commercial motion for {name}",
                "type": "people",
                "impact": "medium",
                "likelihood": "medium",
                "mitigation": "Track adoption by team and reinforce manager coaching routines.",
                "rationale": "Sales behavior change is a primary dependency for revenue uplift.",
            },
        ],
        "cost_reduction": [
            {
                "description": "Savings leakage may reduce realized value from {name}",
                "type": "financial",
                "impact": "high",
                "likelihood": "medium",
                "mitigation": "Lock savings into budgets and validate run-rate impact with Finance.",
                "rationale": "Cost reductions can be offset by backfill, exceptions, or unmanaged demand.",
            },
            {
                "description": "Process disruption may affect service levels during {name}",
                "type": "operational",
                "impact": "medium",
                "likelihood": "medium",
                "mitigation": "Define service-level guardrails and monitor exceptions during rollout.",
                "rationale": "Efficiency initiatives can degrade delivery quality if unmanaged.",
            },
        ],
        "cost_avoidance": [
            {
                "description": "Exposure underestimation may reduce avoided value from {name}",
                "type": "financial",
                "impact": "high",
                "likelihood": "medium",
                "mitigation": "Validate exposure assumptions with Finance and refresh the avoided-cost baseline monthly.",
                "rationale": "Cost-avoidance initiatives depend on credible exposure baselines.",
            },
            {
                "description": "Control bypass may allow future cost growth during {name}",
                "type": "operational",
                "impact": "medium",
                "likelihood": "medium",
                "mitigation": "Add control checks, exception reporting, and accountable owners for bypass requests.",
                "rationale": "Avoided costs can reappear when teams bypass the prevention mechanism.",
            },
        ],
        "compliance": [
            {
                "description": "Control evidence may be incomplete for {name}",
                "type": "operational",
                "impact": "high",
                "likelihood": "medium",
                "mitigation": "Define evidence owners, sample cadence, and audit-ready storage.",
                "rationale": "Compliance outcomes depend on durable evidence, not just implementation.",
            },
            {
                "description": "Regulatory interpretation may change during {name}",
                "type": "technology",
                "impact": "medium",
                "likelihood": "low",
                "mitigation": "Schedule legal/compliance checkpoint reviews before each gate.",
                "rationale": "External requirements can shift while remediation is in flight.",
            },
        ],
        "capability_building": [
            {
                "description": "Training completion may not translate into behavior change for {name}",
                "type": "people",
                "impact": "medium",
                "likelihood": "high",
                "mitigation": "Pair training with manager routines, usage metrics, and reinforcement cycles.",
                "rationale": "Capability programs fail when measured only by attendance.",
            },
            {
                "description": "New standards may not be embedded into daily work for {name}",
                "type": "operational",
                "impact": "medium",
                "likelihood": "medium",
                "mitigation": "Add adherence checks to governance routines and operating dashboards.",
                "rationale": "Operating-model changes need recurring management reinforcement.",
            },
        ],
    }
    return [*by_type.get(initiative_type or "", []), *common]


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


def _field_prompt(masked_text: str) -> str:
    return (
        "Extract these fields from the initiative description: name, type, priority, "
        "workstream, country, summary, value_logic, planned_end, dependencies. "
        "Allowed type values: revenue_growth, cost_reduction, cost_avoidance, compliance, "
        "capability_building. Allowed priority values: high, medium, low. "
        "Return null for fields that are not directly supported by the text.\n\n"
        f"Description:\n{masked_text}"
    )


def _masked_free_text(text: str) -> str:
    masked = re.sub(r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}", "[masked_email]", text)
    return re.sub(r"\+?\d[\d\s().-]{7,}\d", _mask_phone_like_value, masked)


def _mask_phone_like_value(match: re.Match[str]) -> str:
    value = match.group(0)
    if re.fullmatch(r"20\d{2}-(0[1-9]|1[0-2])-(0[1-9]|[12]\d|3[01])", value):
        return value
    return "[masked_phone]"


def _collapse(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def _extract_name(text: str) -> str | None:
    labeled = _extract_labeled_text(text, ("initiative", "name", "project"))
    if labeled:
        return labeled[:300]
    quoted = re.search(r"['\"]([^'\"]{4,120})['\"]", text)
    if quoted:
        return quoted.group(1).strip()
    first_sentence = re.split(r"(?<=[.!?])\s+", text, maxsplit=1)[0].strip()
    return first_sentence[:120] if 4 <= len(first_sentence) <= 120 else None


def _extract_type(lowered: str) -> str | None:
    patterns = (
        (
            "revenue_growth",
            ("revenue growth", "sales growth", "commercial growth", "uplift revenue"),
        ),
        ("cost_reduction", ("cost reduction", "cost savings", "reduce cost", "opex reduction")),
        ("cost_avoidance", ("cost avoidance", "avoid cost", "cost avoided")),
        ("compliance", ("compliance", "regulatory", "audit requirement")),
        ("capability_building", ("capability", "training", "enablement", "operating model")),
    )
    for value, needles in patterns:
        if any(needle in lowered for needle in needles):
            return value
    return None


def _extract_priority(lowered: str) -> str | None:
    for value in ("high", "medium", "low"):
        if re.search(rf"\b{value}\s+priority\b|\bpriority\s*[:=-]\s*{value}\b", lowered):
            return value
    return None


def _extract_labeled_text(text: str, labels: tuple[str, ...]) -> str | None:
    label_pattern = "|".join(re.escape(label) for label in labels)
    match = re.search(
        rf"(?:{label_pattern})\s*[:=-]\s*([^.;\n]+)",
        text,
        flags=re.IGNORECASE,
    )
    if match:
        return match.group(1).strip()[:500] or None
    return None


def _extract_summary(text: str) -> str | None:
    summary = _extract_labeled_text(text, ("summary", "description"))
    if summary:
        return summary
    sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", text) if s.strip()]
    return sentences[0][:500] if sentences else None


def _extract_date(text: str) -> date | None:
    iso = re.search(r"\b(20\d{2})-(0[1-9]|1[0-2])-(0[1-9]|[12]\d|3[01])\b", text)
    if iso:
        try:
            return date.fromisoformat(iso.group(0))
        except ValueError:
            return None
    month = re.search(
        r"\b(?:by|end|complete(?:d)? by)\s+"
        r"(Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|"
        r"Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)\s+"
        r"(20\d{2})\b",
        text,
        flags=re.IGNORECASE,
    )
    if not month:
        return None
    month_lookup = {
        "jan": 1,
        "feb": 2,
        "mar": 3,
        "apr": 4,
        "may": 5,
        "jun": 6,
        "jul": 7,
        "aug": 8,
        "sep": 9,
        "oct": 10,
        "nov": 11,
        "dec": 12,
    }
    month_num = month_lookup[month.group(1)[:3].lower()]
    return date(int(month.group(2)), month_num, 1)


def _estimate_tokens(text: str) -> int:
    return max(1, len(re.findall(r"\S+", text)))


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
    suggestions.trace_url = langfuse.get_trace_url(trace_id=trace_id) if langfuse else None
    return suggestions


def _with_field_trace(
    result: InitiativeFieldExtractionResult,
    trace_id: str,
    langfuse: Langfuse | None,
    input_tokens: int,
) -> InitiativeFieldExtractionResult:
    result.trace_id = trace_id
    result.trace_url = langfuse.get_trace_url(trace_id=trace_id) if langfuse else None
    result.input_tokens = input_tokens
    if result.output_tokens <= 0:
        result.output_tokens = _estimate_tokens(result.draft.model_dump_json(exclude_none=True))
    return result


def _fill_missing_draft_fields(target: InitiativeDraft, fallback: InitiativeDraft) -> None:
    for field, value in fallback.model_dump().items():
        if getattr(target, field) is None and value is not None:
            setattr(target, field, value)
