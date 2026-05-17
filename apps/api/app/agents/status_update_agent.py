"""Status update drafting skill with deterministic grounding."""

from __future__ import annotations

from uuid import uuid4

from langfuse.types import TraceContext

from app.agents.initiative_intake_agent import _get_langfuse
from app.core.config import settings
from app.domain.initiative_context import InitiativeContextPullResult
from app.domain.status_updates import StatusUpdateDraftSuggestion


def draft_status_update(context: InitiativeContextPullResult) -> StatusUpdateDraftSuggestion:
    """Draft a status update only from supplied initiative context."""
    trace_id = _trace_id()
    milestones = context.milestones_summary
    risks = context.risks_summary
    kpis = context.kpis_summary.kpis
    financials = context.financials_summary
    rag_status = _rag_status(context)
    completed = [item.name for item in milestones.completed_this_period]
    off_track_kpis = [item.name for item in kpis if not item.on_track]

    summary = (
        f"This period has {milestones.complete} of {milestones.total} milestones complete, "
        f"{risks.open_high} high and {risks.open_medium} medium open risks, and "
        f"{len(off_track_kpis)} KPIs needing attention. "
        f"Financial progress shows revenue actual {financials.revenue_actual} against plan "
        f"{financials.revenue_plan}, with costs actual {financials.costs_actual} against plan "
        f"{financials.costs_plan}."
    )
    if context.last_update:
        summary += f" The previous submitted update was {context.last_update.rag_status}."

    result = StatusUpdateDraftSuggestion(
        trace_id=trace_id,
        rag_status=rag_status,
        summary=summary,
        achievements=_achievement_bullets(completed),
        issues=_issue_bullets(context, off_track_kpis),
        next_steps=_next_step_bullets(context, off_track_kpis),
        confidence=_confidence(context),
        sources=context.sources,
    )
    return _trace_status_update(context, result)


def _rag_status(context: InitiativeContextPullResult) -> str:
    milestones = context.milestones_summary
    risks = context.risks_summary
    kpis = context.kpis_summary.kpis
    if milestones.overdue > 0 or risks.open_high > 0:
        return "red"
    if milestones.at_risk > 0 or risks.open_medium > 0 or any(not item.on_track for item in kpis):
        return "amber"
    return "green"


def _achievement_bullets(completed: list[str]) -> str:
    if completed:
        return "\n".join(f"- Completed {name}." for name in completed)
    return "- No completed milestones were recorded this period."


def _issue_bullets(context: InitiativeContextPullResult, off_track_kpis: list[str]) -> str:
    lines: list[str] = []
    risks = context.risks_summary
    milestones = context.milestones_summary
    if milestones.overdue:
        lines.append(f"- {milestones.overdue} overdue milestones require attention.")
    if risks.open_high:
        lines.append(f"- {risks.open_high} high risks remain open.")
    if risks.open_medium:
        lines.append(f"- {risks.open_medium} medium risks remain open.")
    if off_track_kpis:
        lines.append(f"- Off-track KPIs: {', '.join(off_track_kpis[:3])}.")
    return "\n".join(lines) if lines else "- No material blockers are present in the supplied context."


def _next_step_bullets(context: InitiativeContextPullResult, off_track_kpis: list[str]) -> str:
    lines = []
    if context.milestones_summary.overdue or context.milestones_summary.at_risk:
        lines.append("- Resolve overdue or at-risk milestone owners before the next checkpoint.")
    if context.risks_summary.open_high or context.risks_summary.open_medium:
        lines.append("- Review open risk mitigations and confirm current ownership.")
    if off_track_kpis:
        lines.append("- Refresh KPI evidence and recovery actions for off-track metrics.")
    if not lines:
        lines.append("- Continue execution cadence and refresh evidence before the next update.")
    return "\n".join(lines)


def _confidence(context: InitiativeContextPullResult) -> float:
    score = 0.55
    if context.milestones_summary.total:
        score += 0.12
    if context.kpis_summary.kpis:
        score += 0.12
    if context.risks_summary.open_high or context.risks_summary.open_medium:
        score += 0.08
    if context.last_update:
        score += 0.08
    if context.financials_summary.revenue_plan != "0.0000" or context.financials_summary.costs_plan != "0.0000":
        score += 0.05
    return round(min(score, 0.95), 2)


def _trace_id() -> str:
    langfuse = _get_langfuse()
    if langfuse:
        return langfuse.create_trace_id(seed=f"status-update-drafting-{uuid4()}")
    return f"deterministic-status-update-{uuid4()}"


def _trace_status_update(
    context: InitiativeContextPullResult,
    result: StatusUpdateDraftSuggestion,
) -> StatusUpdateDraftSuggestion:
    langfuse = _get_langfuse()
    if not langfuse or not result.trace_id:
        return result
    try:
        with langfuse.start_as_current_observation(
            name="status_update_drafting",
            as_type="agent",
            trace_context=TraceContext(trace_id=result.trace_id),
            input={
                "initiative_id": context.initiative_id,
                "period_start": context.period_start,
                "period_end": context.period_end,
                "sources": context.sources,
            },
            metadata={"source": "status_update_generation"},
            model=settings.default_model,
        ):
            result.trace_url = langfuse.get_trace_url(trace_id=result.trace_id)
            langfuse.update_current_span(output=result.model_dump(mode="json"))
        langfuse.flush()
    except Exception:
        result.trace_url = None
    return result
