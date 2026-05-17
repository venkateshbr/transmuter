from __future__ import annotations

import pytest

from app.agents.status_update_agent import draft_status_update
from app.core.config import settings
from app.domain.initiative_context import (
    CompletedMilestoneContext,
    FinancialsContextSummary,
    InitiativeContextPullResult,
    KPIContextItem,
    KPIsContextSummary,
    LastStatusUpdateContext,
    MilestonesContextSummary,
    NewRiskContext,
    RisksContextSummary,
)
from app.domain.status_updates import StatusUpdateDraftSuggestion


@pytest.fixture(autouse=True)
def disable_langfuse(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "ai_enabled", False)


def test_status_update_drafting_derives_red_from_high_risk_and_overdue() -> None:
    context = _context(
        milestones_summary=MilestonesContextSummary(
            total=3,
            complete=1,
            overdue=1,
            at_risk=1,
            completed_this_period=[
                CompletedMilestoneContext(name="Baseline complete", completed_at="2026-05-10")
            ],
        ),
        risks_summary=RisksContextSummary(
            open_high=1,
            open_medium=0,
            new_this_period=[NewRiskContext(description="ERP dependency may slip")],
        ),
        kpis_summary=KPIsContextSummary(
            kpis=[
                KPIContextItem(
                    name="Cycle time reduction",
                    target_base="12.0000",
                    latest_actual="8.0000",
                    on_track=False,
                )
            ]
        ),
    )

    draft = draft_status_update(context)

    assert isinstance(draft, StatusUpdateDraftSuggestion)
    assert draft.rag_status == "red"
    assert "Completed Baseline complete" in (draft.achievements or "")
    assert "1 high risks remain open" in (draft.issues or "")
    assert "Cycle time reduction" in (draft.issues or "")
    assert draft.confidence >= 0.8
    assert "unrelated" not in draft.summary.lower()


def test_status_update_drafting_uses_green_when_context_has_no_issues() -> None:
    context = _context(
        milestones_summary=MilestonesContextSummary(
            total=1,
            complete=1,
            completed_this_period=[CompletedMilestoneContext(name="Pilot complete")],
        ),
        risks_summary=RisksContextSummary(),
        kpis_summary=KPIsContextSummary(
            kpis=[
                KPIContextItem(
                    name="Adoption rate",
                    target_base="70.0000",
                    latest_actual="75.0000",
                    on_track=True,
                )
            ]
        ),
    )

    draft = draft_status_update(context)

    assert draft.rag_status == "green"
    assert "No material blockers" in (draft.issues or "")
    assert draft.confidence > 0


def _context(
    *,
    milestones_summary: MilestonesContextSummary,
    risks_summary: RisksContextSummary,
    kpis_summary: KPIsContextSummary,
) -> InitiativeContextPullResult:
    return InitiativeContextPullResult(
        initiative_id="init-1",
        period_start="2026-05-01",
        period_end="2026-05-31",
        milestones_summary=milestones_summary,
        kpis_summary=kpis_summary,
        risks_summary=risks_summary,
        financials_summary=FinancialsContextSummary(
            revenue_plan="100.0000",
            revenue_actual="90.0000",
            costs_plan="10.0000",
            costs_actual="8.0000",
        ),
        last_update=LastStatusUpdateContext(
            rag_status="amber",
            submitted_at="2026-04-30T00:00:00+00:00",
            summary="Previous update was amber.",
        ),
        sources=["milestones", "risks", "kpis", "financial_entries"],
    )
