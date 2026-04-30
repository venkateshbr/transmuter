"""
Pressure score engine — deterministic formula from pressure_formula.yaml.
Phase 1 stub: returns 0.0 for all components; full formula in G1-3 (#40).
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal


@dataclass
class MilestonePressureResult:
    total: Decimal
    blast_radius: Decimal
    dependent_urgency: Decimal
    cluster_bonus: Decimal
    slack_penalty: Decimal
    checklist: Decimal
    self_status: Decimal


@dataclass
class InitiativePressureResult:
    total: Decimal
    schedule: Decimal
    milestone_health: Decimal
    risk_exposure: Decimal
    kpi_performance: Decimal
    financial: Decimal
    self_reported: Decimal


ZERO = Decimal("0.0")


def calculate_milestone_pressure(milestone_id: str, db_row: dict) -> MilestonePressureResult:  # type: ignore[type-arg]
    """Stub — returns 0. Replace with full formula in G1-3."""
    return MilestonePressureResult(
        total=ZERO, blast_radius=ZERO, dependent_urgency=ZERO,
        cluster_bonus=ZERO, slack_penalty=ZERO, checklist=ZERO, self_status=ZERO,
    )


def calculate_initiative_pressure(initiative_id: str, db_data: dict) -> InitiativePressureResult:  # type: ignore[type-arg]
    """Stub — returns 0. Replace with full formula in G1-3."""
    return InitiativePressureResult(
        total=ZERO, schedule=ZERO, milestone_health=ZERO,
        risk_exposure=ZERO, kpi_performance=ZERO, financial=ZERO, self_reported=ZERO,
    )
