"""Pressure score engine — fully deterministic, formula-driven.

Implements the spec from domain_packs/transmuter/pressure_formula.yaml.
All calculations use Decimal arithmetic. Never float.
Scale: 0–10. Thresholds: Low 0–3.3, Medium 3.4–6.6, High 6.7–10.
"""

from __future__ import annotations

from datetime import date, datetime
from decimal import ROUND_HALF_UP, Decimal

from pydantic import BaseModel

# ── Helpers ──────────────────────────────────────────────────────────

D0 = Decimal("0")
D1 = Decimal("1")


def clamp(
    value: Decimal,
    min_val: Decimal,
    max_val: Decimal,
) -> Decimal:
    return max(min_val, min(value, max_val))


def round_pressure(value: Decimal) -> Decimal:
    return value.quantize(Decimal("0.1"), rounding=ROUND_HALF_UP)


def round_sub(value: Decimal) -> Decimal:
    return value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def _today() -> date:
    return datetime.now().date()


def _parse_date(raw: object) -> date | None:
    if raw is None:
        return None
    if isinstance(raw, date):
        return raw
    return date.fromisoformat(str(raw))


def pressure_level(score: Decimal) -> str:
    if score <= Decimal("3.3"):
        return "low"
    if score <= Decimal("6.6"):
        return "medium"
    return "high"


# ── Result models ────────────────────────────────────────────────────


class MilestonePressureResult(BaseModel):
    pressure_score: str
    level: str
    blast_radius: str
    dep_urgency: str
    cluster: str
    slack: str
    checklist: str
    self_status: str


class InitiativePressureResult(BaseModel):
    pressure_score: str
    level: str
    schedule: str
    milestone_health: str
    risk_exposure: str
    kpi_performance: str
    financial: str
    self_reported: str


# ── Milestone Pressure Engine ────────────────────────────────────────


class MilestonePressureEngine:
    """Calculate pressure for a single milestone."""

    @staticmethod
    def calculate(
        milestone: dict,  # type: ignore[type-arg]
        downstream_milestones: list[dict],  # type: ignore[type-arg]
        transitive_count: int,
        sibling_milestones: list[dict],  # type: ignore[type-arg]
        checklist_stats: tuple[int, int],
    ) -> MilestonePressureResult:
        today = _today()
        blast = _blast_radius(downstream_milestones, transitive_count)
        dep = _dep_urgency(downstream_milestones, today)
        cl = _cluster_bonus(sibling_milestones, today)
        slk = _slack_penalty(milestone, today)
        chk = _checklist_score(checklist_stats)
        ss = _self_status(milestone, today)

        total = clamp(
            blast + dep + cl + slk + chk + ss,
            D0,
            Decimal("10"),
        )
        return MilestonePressureResult(
            pressure_score=str(round_pressure(total)),
            level=pressure_level(total),
            blast_radius=str(round_sub(blast)),
            dep_urgency=str(round_sub(dep)),
            cluster=str(round_sub(cl)),
            slack=str(round_sub(slk)),
            checklist=str(round_sub(chk)),
            self_status=str(round_sub(ss)),
        )


# ── Sub-score functions ──────────────────────────────────────────────


def _blast_radius(
    downstream: list[dict],  # type: ignore[type-arg]
    transitive_count: int,
) -> Decimal:
    direct = Decimal(str(len(downstream)))
    indirect = Decimal(str(transitive_count))
    weighted = (direct * D1) + (indirect * Decimal("0.4"))
    return clamp(weighted, D0, Decimal("3.5"))


def _dep_urgency(
    downstream: list[dict],  # type: ignore[type-arg]
    today: date,
) -> Decimal:
    total = D0
    for ms in downstream:
        due = _parse_date(ms.get("planned_end"))
        if not due:
            continue
        days = (due - today).days
        if days < 0:
            u = Decimal("1.0")
        elif days <= 7:
            u = Decimal("0.85")
        elif days <= 14:
            u = Decimal("0.60")
        elif days <= 30:
            u = Decimal("0.35")
        elif days <= 60:
            u = Decimal("0.15")
        else:
            u = D0
        total += u
    return clamp(total, D0, Decimal("2.5"))


def _cluster_bonus(
    siblings: list[dict],  # type: ignore[type-arg]
    today: date,
) -> Decimal:
    struggling = 0
    for s in siblings:
        status = s.get("status", "")
        due = _parse_date(s.get("planned_end"))
        p = s.get("pressure_score")
        is_struggling = (
            status == "overdue"
            or (status != "complete" and due and due < today)
            or (p is not None and Decimal(str(p)) > Decimal("6.0"))
        )
        if is_struggling:
            struggling += 1
    return clamp(
        Decimal(str(struggling)) * Decimal("0.5"),
        D0,
        Decimal("1.5"),
    )


def _slack_penalty(
    milestone: dict,
    today: date,  # type: ignore[type-arg]
) -> Decimal:
    if milestone.get("status") == "complete":
        return D0
    planned_end = _parse_date(milestone.get("planned_end"))
    if not planned_end:
        return D0
    if planned_end < today:
        return Decimal("1.5")

    planned_start = _parse_date(milestone.get("planned_start"))
    if planned_start:
        total_dur = max((planned_end - planned_start).days, 1)
        remaining = (planned_end - today).days
        slack_ratio = Decimal(str(remaining)) / Decimal(str(total_dur))
        elapsed = D1 - slack_ratio
        if elapsed <= D0:
            return D0
        # Curve: elapsed^1.5 * 1.5, using Decimal arithmetic.
        raw = elapsed * elapsed.sqrt() * Decimal("1.5")
        return clamp(raw, D0, Decimal("1.5"))

    # Absolute days fallback
    days_remaining = (planned_end - today).days
    if days_remaining <= 0:
        return Decimal("1.5")
    if days_remaining <= 7:
        return Decimal("1.2")
    if days_remaining <= 14:
        return Decimal("0.8")
    if days_remaining <= 30:
        return Decimal("0.4")
    if days_remaining <= 60:
        return Decimal("0.15")
    return D0


def _checklist_score(stats: tuple[int, int]) -> Decimal:
    total, completed = stats
    if total == 0:
        return D0
    incomplete = total - completed
    pct = Decimal(str(incomplete)) / Decimal(str(total))
    return pct * Decimal("0.5")


def _self_status(
    milestone: dict,
    today: date,  # type: ignore[type-arg]
) -> Decimal:
    status = milestone.get("status", "not_started")
    if status == "complete":
        return D0
    if status == "overdue":
        return Decimal("0.5")
    if status == "in_progress":
        return Decimal("0.2")
    if status == "not_started":
        ps = _parse_date(milestone.get("planned_start"))
        if ps and ps < today:
            days_late = (today - ps).days
            return clamp(
                Decimal("0.1") + Decimal(str(days_late)) * Decimal("0.02"),
                Decimal("0.1"),
                Decimal("0.5"),
            )
        return Decimal("0.1")
    return D0
