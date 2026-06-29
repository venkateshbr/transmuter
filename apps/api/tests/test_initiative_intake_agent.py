from __future__ import annotations

from datetime import date

from app.agents.initiative_intake_agent import (
    deterministic_initiative_narrative,
    deterministic_intake_suggestions,
)
from app.domain.initiative_intake import InitiativeIntakeRequest
from app.domain.initiatives import InitiativeCreate


def _request() -> InitiativeIntakeRequest:
    return InitiativeIntakeRequest(
        initiative=InitiativeCreate(
            name="S3 Accounting Automation",
            type="cost_reduction",
            impact_type="recurring",
            country="Singapore",
            theme="Finance operations",
            priority="high",
            planned_start=date(2026, 7, 1),
            planned_end=date(2026, 12, 31),
        ),
        conversation=[],
    )


def test_deterministic_intake_suggestions_do_not_generate_financials() -> None:
    suggestions = deterministic_intake_suggestions(_request())

    assert suggestions.financial_entries == []
    assert suggestions.cost_lines == []
    assert suggestions.kpis
    assert suggestions.risks
    assert suggestions.milestones


def test_deterministic_initiative_narrative_populates_narrative_fields() -> None:
    result = deterministic_initiative_narrative(_request())

    assert result.draft.summary
    assert result.draft.context_problem
    assert result.draft.value_logic
    assert result.draft.dependencies
    assert "Financial benefits should be modeled separately" in result.draft.value_logic
