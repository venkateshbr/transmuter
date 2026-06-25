"""Unit tests for the deterministic pressure score engine."""

from datetime import date
from decimal import Decimal

from app.domain.pressure import (
    _blast_radius,
    _checklist_score,
    _cluster_bonus,
    _dep_urgency,
    _self_status,
    _slack_penalty,
)
from app.repositories.initiative import InitiativeRepository


def _ms(
    status: str = "not_started",
    planned_start: str | None = None,
    planned_end: str | None = None,
    pressure_score: str | None = None,
) -> dict:  # type: ignore[type-arg]
    return {
        "id": "123",
        "initiative_id": "456",
        "status": status,
        "planned_start": planned_start,
        "planned_end": planned_end,
        "pressure_score": pressure_score,
    }


def test_blast_radius():
    # 0 dependents -> 0
    assert _blast_radius([], 0) == Decimal("0")

    # 1 direct -> 1.0
    assert _blast_radius([{}], 0) == Decimal("1.0")

    # 2 direct -> 2.0
    assert _blast_radius([{}, {}], 0) == Decimal("2.0")

    # 3 direct + 2 indirect -> 3.5 (capped at 3.5)
    # 3 * 1.0 + 2 * 0.4 = 3.8 -> 3.5
    assert _blast_radius([{}, {}, {}], 2) == Decimal("3.5")


def test_dependent_urgency():
    today = date(2026, 5, 1)

    # No dependents
    assert _dep_urgency([], today) == Decimal("0")

    # 1 dependent due in 3 days -> 0.85
    ds1 = [{"planned_end": "2026-05-04"}]
    assert _dep_urgency(ds1, today) == Decimal("0.85")

    # 2 dependents due in <7 days -> 1.7
    ds2 = [{"planned_end": "2026-05-04"}, {"planned_end": "2026-05-05"}]
    assert _dep_urgency(ds2, today) == Decimal("1.70")

    # 3+ urgent dependents -> 2.5 (capped)
    ds3 = [
        {"planned_end": "2026-05-02"},
        {"planned_end": "2026-05-03"},
        {"planned_end": "2026-05-04"},
    ]
    # 3 * 0.85 = 2.55 -> 2.5
    assert _dep_urgency(ds3, today) == Decimal("2.5")


def test_cluster_bonus():
    today = date(2026, 5, 1)

    # 0 struggling
    assert _cluster_bonus([], today) == Decimal("0")

    # 1 struggling (overdue)
    sib1 = [{"status": "overdue"}]
    assert _cluster_bonus(sib1, today) == Decimal("0.5")

    # 2 struggling (1 overdue, 1 due date passed)
    sib2 = [{"status": "overdue"}, {"status": "in_progress", "planned_end": "2026-04-30"}]
    assert _cluster_bonus(sib2, today) == Decimal("1.0")

    # 3+ struggling -> 1.5 (capped)
    sib3 = [
        {"status": "overdue"},
        {"status": "in_progress", "planned_end": "2026-04-30"},
        {"pressure_score": "7.5"},  # high pressure sibling
        {"status": "overdue"},
    ]
    assert _cluster_bonus(sib3, today) == Decimal("1.5")


def test_slack_penalty():
    today = date(2026, 5, 1)

    # Complete -> 0.0
    assert _slack_penalty(_ms("complete"), today) == Decimal("0")

    # Overdue -> 1.5
    assert _slack_penalty(_ms(planned_end="2026-04-30"), today) == Decimal("1.5")

    # 50% elapsed -> ~0.53 ( (0.5)^1.5 * 1.5 = 0.5303 )
    ms_50 = _ms(planned_start="2026-04-01", planned_end="2026-05-31")
    assert round(_slack_penalty(ms_50, today), 2) == Decimal("0.53")

    # 7 days left (no start date) -> 1.2
    ms_abs = _ms(planned_end="2026-05-08")
    assert _slack_penalty(ms_abs, today) == Decimal("1.2")


def test_checklist():
    # No checklist
    assert _checklist_score((0, 0)) == Decimal("0")

    # All items complete
    assert _checklist_score((5, 5)) == Decimal("0")

    # Half complete
    assert _checklist_score((4, 2)) == Decimal("0.25")

    # Nothing done
    assert _checklist_score((3, 0)) == Decimal("0.5")


def test_self_status():
    today = date(2026, 5, 10)

    # Complete -> 0.0
    assert _self_status(_ms("complete"), today) == Decimal("0")

    # Not started (future) -> 0.1
    assert _self_status(_ms("not_started", "2026-06-01"), today) == Decimal("0.1")

    # In progress -> 0.2
    assert _self_status(_ms("in_progress"), today) == Decimal("0.2")

    # Not started but 10 days past planned start -> 0.3
    # 0.1 + (10 * 0.02) = 0.3
    assert _self_status(_ms("not_started", "2026-04-30"), today) == Decimal("0.3")

    # Overdue -> 0.5
    assert _self_status(_ms("overdue"), today) == Decimal("0.5")


def test_initiative_count_treats_past_due_incomplete_milestone_as_overdue():
    assert InitiativeRepository._milestone_is_overdue(
        {"status": "not_started", "planned_end": "2026-01-01"}
    )
    assert not InitiativeRepository._milestone_is_overdue(
        {"status": "complete", "planned_end": "2026-01-01"}
    )
