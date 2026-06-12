from __future__ import annotations

from datetime import date
from uuid import uuid4

import pytest

from app.agents.initiative_intake_agent import (
    deterministic_field_extraction,
    scan_risk_patterns,
    suggest_kpis,
)
from app.agents.meeting_notes_agent import (
    chunk_transcript,
    extract_action_items,
    extract_meeting_decisions,
)
from app.agents.status_update_agent import draft_status_update
from app.domain.initiative_context import (
    FinancialsContextSummary,
    InitiativeContextPullResult,
    KPIContextItem,
    KPIsContextSummary,
    MilestonesContextSummary,
    RisksContextSummary,
)
from app.domain.initiative_intake import InitiativeDraft
from app.domain.meeting_notes import LinkedInitiativeContext, MeetingAttendeeContext


def test_initiative_field_extraction_is_conservative_and_masks_pii() -> None:
    result = deterministic_field_extraction(
        "Initiative: Korea pricing launch. Type: revenue growth. Priority: high. "
        "Market: Korea. Value logic: gross margin uplift. Complete by June 2026. "
        "Contact owner@example.com for details."
    )

    assert result.draft.name == "Korea pricing launch"
    assert result.draft.type == "revenue_growth"
    assert result.draft.priority == "high"
    assert result.draft.country == "Korea"
    assert result.draft.planned_end == date(2026, 6, 1)
    assert "owner@example.com" not in result.model_dump_json()
    assert result.confidence > 0.5


def test_kpi_and_risk_suggestion_patterns_are_domain_specific() -> None:
    kpis = suggest_kpis("cost_reduction", "AP automation", "reduce cycle time")
    risks = scan_risk_patterns(
        InitiativeDraft(
            name="AP automation",
            type="cost_reduction",
            dependencies="ERP interface",
        )
    )

    assert 3 <= len(kpis.suggestions) <= 5
    assert any(item.name == "Run-rate savings realized" for item in kpis.suggestions)
    assert 2 <= len(risks.risks) <= 4
    assert any("Savings leakage" in item.description for item in risks.risks)


def test_meeting_notes_skills_extract_actions_decisions_and_updates() -> None:
    chunks = chunk_transcript(
        "Rupa Menon: Action: confirm ERP integration owner by 2026-06-10.\n\n"
        "Vishwa Rao: Decision: Korea launch waits on pricing governance.\n\n"
        "Rupa Menon: AP Automation is blocked and amber until ERP is signed off."
    ).chunks

    actions = extract_action_items(
        chunks,
        [MeetingAttendeeContext(user_id="user-1", display_name="Rupa Menon")],
    )
    decisions = extract_meeting_decisions(
        chunks,
        [LinkedInitiativeContext(id="init-1", name="AP Automation", initiative_code="TRN-002")],
    )

    assert actions.action_items[0].suggested_assignee_id == "user-1"
    assert actions.action_items[0].due_date == "2026-06-10"
    assert decisions.decisions
    assert decisions.initiative_updates[0].rag_status == "amber"


@pytest.mark.asyncio
async def test_status_update_drafting_uses_only_context_facts(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("app.agents.status_update_agent.settings.ai_enabled", False)
    context = InitiativeContextPullResult(
        initiative_id=str(uuid4()),
        period_start="2026-04-01",
        period_end="2026-06-30",
        milestones_summary=MilestonesContextSummary(total=3, complete=1, overdue=1),
        kpis_summary=KPIsContextSummary(
            kpis=[KPIContextItem(name="Cycle time", target_base="20.0000", latest_actual="12.0000")]
        ),
        risks_summary=RisksContextSummary(open_high=1, open_medium=0),
        financials_summary=FinancialsContextSummary(
            revenue_plan="100000.0000",
            revenue_actual="70000.0000",
            costs_plan="25000.0000",
            costs_actual="30000.0000",
        ),
        sources=["milestones", "kpis", "risks", "financial_entries"],
    )

    draft = await draft_status_update(context)

    assert draft.rag_status == "red"
    assert "1 high risks" in draft.summary
    assert "Cycle time" in (draft.issues or "")
    assert draft.confidence >= 0.8
