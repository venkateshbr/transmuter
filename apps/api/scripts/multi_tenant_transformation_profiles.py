"""Deterministic company profiles for multi-tenant transformation testing."""

from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import dataclass
from decimal import Decimal
from typing import cast

type InitiativeSeedRow = tuple[
    str,
    str,
    str,
    str,
    str,
    str,
    Decimal,
    Decimal,
    Decimal,
    Decimal,
    Decimal,
    Decimal,
    Decimal,
    Decimal,
    Decimal,
    Decimal,
]
type InitiativeStructure = tuple[str, str, str, str]

_EXPECTED_CODES = tuple(f"ENT-{index:03d}" for index in range(1, 11))
_SLUG_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


@dataclass(frozen=True, slots=True)
class CompanyProfile:
    """Immutable company-specific inputs layered over the canonical seed rows."""

    name: str
    slug: str
    email_domain: str
    admin_display_name: str
    admin_title: str
    currency: str
    fiscal_start_month: int
    baseline_revenue: Decimal
    baseline_gross_margin: Decimal
    value_scale: Decimal
    country: str
    theme: str
    initiative_names: tuple[str, ...]
    initiative_structures: tuple[InitiativeStructure, ...]
    initiative_value_factors: tuple[Decimal, ...]

    def __post_init__(self) -> None:
        text_values = (
            self.name,
            self.admin_display_name,
            self.admin_title,
            self.country,
            self.theme,
        )
        if any(not value.strip() for value in text_values):
            raise ValueError("Company profile text fields must not be blank")
        if not _SLUG_PATTERN.fullmatch(self.slug):
            raise ValueError("Company profile slug must use lowercase letters, digits, and hyphens")
        if "@" in self.email_domain or not self.email_domain.endswith(".transmuter.test"):
            raise ValueError(
                "Company profile email domain must use the reserved .transmuter.test suffix"
            )
        if len(self.currency) != 3 or not self.currency.isalpha() or not self.currency.isupper():
            raise ValueError("Company profile currency must be an uppercase 3-letter code")
        if not 1 <= self.fiscal_start_month <= 12:
            raise ValueError("Company profile fiscal start month must be between 1 and 12")
        if self.baseline_revenue <= 0 or self.baseline_gross_margin <= 0:
            raise ValueError("Company profile financial baselines must be positive")
        if self.value_scale <= 0:
            raise ValueError("Company profile value scale must be positive")
        if len(self.initiative_names) != 10:
            raise ValueError("Company profile must define exactly 10 initiative names")
        if len(set(self.initiative_names)) != 10 or any(
            not name.strip() for name in self.initiative_names
        ):
            raise ValueError("Company profile initiative names must be unique and non-blank")
        if len(self.initiative_structures) != 10:
            raise ValueError("Company profile must define exactly 10 initiative structures")
        allowed_business_units = {
            "Corporate",
            "Commercial",
            "Operations",
            "Technology",
            "Shared Services",
        }
        allowed_workstreams = {
            "Automation",
            "Offshoring & Operating Model",
            "Commercial Growth",
            "ERP & Data Platform",
            "Procurement & Supply Chain",
        }
        allowed_tags = {"automation", "offshoring", "commercial", "other"}
        allowed_types = {
            "revenue_growth",
            "cost_reduction",
            "cost_avoidance",
            "compliance",
            "capability_building",
        }
        if any(
            business_unit not in allowed_business_units
            or workstream not in allowed_workstreams
            or tag not in allowed_tags
            or initiative_type not in allowed_types
            for business_unit, workstream, tag, initiative_type in self.initiative_structures
        ):
            raise ValueError("Company profile contains an unsupported initiative structure")
        if len(self.initiative_value_factors) != 10 or any(
            factor <= 0 for factor in self.initiative_value_factors
        ):
            raise ValueError("Company profile must define 10 positive initiative value factors")


ACME_STRUCTURES: tuple[InitiativeStructure, ...] = (
    ("Corporate", "Automation", "other", "capability_building"),
    ("Operations", "Automation", "automation", "cost_reduction"),
    ("Commercial", "Commercial Growth", "commercial", "revenue_growth"),
    ("Shared Services", "Offshoring & Operating Model", "offshoring", "cost_reduction"),
    ("Technology", "ERP & Data Platform", "automation", "capability_building"),
    ("Commercial", "Commercial Growth", "commercial", "revenue_growth"),
    ("Commercial", "Commercial Growth", "commercial", "revenue_growth"),
    ("Operations", "Procurement & Supply Chain", "other", "cost_reduction"),
    ("Operations", "Procurement & Supply Chain", "automation", "cost_avoidance"),
    ("Operations", "Automation", "automation", "cost_reduction"),
)

RETAIL_STRUCTURES: tuple[InitiativeStructure, ...] = (
    ("Corporate", "Automation", "other", "capability_building"),
    ("Commercial", "Automation", "commercial", "revenue_growth"),
    ("Commercial", "Commercial Growth", "commercial", "revenue_growth"),
    ("Operations", "Offshoring & Operating Model", "other", "cost_reduction"),
    ("Technology", "ERP & Data Platform", "automation", "capability_building"),
    ("Commercial", "Commercial Growth", "commercial", "revenue_growth"),
    ("Commercial", "Commercial Growth", "commercial", "revenue_growth"),
    ("Operations", "Procurement & Supply Chain", "automation", "cost_avoidance"),
    ("Operations", "Procurement & Supply Chain", "automation", "cost_reduction"),
    ("Operations", "Automation", "other", "cost_reduction"),
)

BANK_STRUCTURES: tuple[InitiativeStructure, ...] = (
    ("Corporate", "Automation", "other", "capability_building"),
    ("Commercial", "Automation", "automation", "revenue_growth"),
    ("Commercial", "Automation", "automation", "cost_avoidance"),
    ("Shared Services", "Offshoring & Operating Model", "offshoring", "cost_reduction"),
    ("Technology", "ERP & Data Platform", "automation", "capability_building"),
    ("Commercial", "Commercial Growth", "commercial", "revenue_growth"),
    ("Commercial", "Commercial Growth", "commercial", "revenue_growth"),
    ("Operations", "Procurement & Supply Chain", "other", "cost_reduction"),
    ("Technology", "ERP & Data Platform", "automation", "compliance"),
    ("Shared Services", "Automation", "automation", "cost_reduction"),
)

HEALTH_STRUCTURES: tuple[InitiativeStructure, ...] = (
    ("Corporate", "Automation", "other", "capability_building"),
    ("Shared Services", "Automation", "automation", "cost_reduction"),
    ("Shared Services", "Automation", "automation", "revenue_growth"),
    ("Operations", "Offshoring & Operating Model", "other", "cost_reduction"),
    ("Technology", "ERP & Data Platform", "automation", "capability_building"),
    ("Commercial", "Commercial Growth", "commercial", "revenue_growth"),
    ("Commercial", "Commercial Growth", "commercial", "revenue_growth"),
    ("Operations", "Procurement & Supply Chain", "other", "cost_reduction"),
    ("Operations", "Procurement & Supply Chain", "automation", "cost_avoidance"),
    ("Technology", "Automation", "automation", "capability_building"),
)

ENERGY_STRUCTURES: tuple[InitiativeStructure, ...] = (
    ("Corporate", "Automation", "other", "capability_building"),
    ("Operations", "Automation", "automation", "cost_avoidance"),
    ("Operations", "Automation", "automation", "cost_reduction"),
    ("Shared Services", "Offshoring & Operating Model", "offshoring", "cost_reduction"),
    ("Technology", "ERP & Data Platform", "automation", "capability_building"),
    ("Commercial", "Commercial Growth", "commercial", "revenue_growth"),
    ("Commercial", "Commercial Growth", "commercial", "revenue_growth"),
    ("Operations", "Procurement & Supply Chain", "other", "cost_reduction"),
    ("Operations", "Procurement & Supply Chain", "automation", "cost_avoidance"),
    ("Operations", "Automation", "automation", "cost_reduction"),
)


COMPANY_PROFILES: tuple[CompanyProfile, ...] = (
    CompanyProfile(
        name="Acme Global Manufacturing",
        slug="qa-e2e-20260712-acme-global-manufacturing",
        email_domain="acme-global-manufacturing.transmuter.test",
        admin_display_name="Acme Transformation Admin",
        admin_title="VP, Enterprise Transformation",
        currency="USD",
        fiscal_start_month=1,
        baseline_revenue=Decimal("20000000"),
        baseline_gross_margin=Decimal("9000000"),
        value_scale=Decimal("1"),
        country="United States",
        theme="Manufacturing productivity and profitable growth",
        initiative_names=(
            "Transformation PMO and Value Office",
            "Smart Factory Automation",
            "Commercial Pricing Excellence",
            "Shared Services Consolidation",
            "Enterprise Data and ERP Modernization",
            "Aftermarket Revenue Growth",
            "Strategic Account Expansion",
            "Strategic Procurement",
            "Supply Chain Control Tower",
            "AI-enabled Predictive Maintenance",
        ),
        initiative_structures=ACME_STRUCTURES,
        initiative_value_factors=(Decimal("1"),) * 10,
    ),
    CompanyProfile(
        name="Northstar Retail Group",
        slug="qa-e2e-20260712-northstar-retail-group",
        email_domain="northstar-retail-group.transmuter.test",
        admin_display_name="Northstar Transformation Admin",
        admin_title="Chief Transformation Officer",
        currency="SGD",
        fiscal_start_month=7,
        baseline_revenue=Decimal("160000000"),
        baseline_gross_margin=Decimal("72000000"),
        value_scale=Decimal("8"),
        country="Singapore",
        theme="Omnichannel retail growth and operating efficiency",
        initiative_names=(
            "Retail Transformation Value Office",
            "Omnichannel Customer Journey",
            "Dynamic Pricing and Markdown Optimization",
            "Store Labor Productivity",
            "Unified Commerce Data Platform",
            "Loyalty and Personalization Growth",
            "Private Label Expansion",
            "Inventory Availability Optimization",
            "Fulfilment Network Modernization",
            "Returns and Waste Reduction",
        ),
        initiative_structures=RETAIL_STRUCTURES,
        initiative_value_factors=tuple(
            Decimal(value)
            for value in ("0.8", "1.3", "1.4", "1.1", "1.2", "1.5", "1.2", "1.1", "1.3", "0.9")
        ),
    ),
    CompanyProfile(
        name="Meridian Commercial Bank",
        slug="qa-e2e-20260712-meridian-commercial-bank",
        email_domain="meridian-commercial-bank.transmuter.test",
        admin_display_name="Meridian Transformation Admin",
        admin_title="Group Transformation Director",
        currency="GBP",
        fiscal_start_month=4,
        baseline_revenue=Decimal("240000000"),
        baseline_gross_margin=Decimal("108000000"),
        value_scale=Decimal("12"),
        country="United Kingdom",
        theme="Digital banking growth, control, and productivity",
        initiative_names=(
            "Bank Transformation Value Office",
            "Digital Client Onboarding",
            "Lending Decision Automation",
            "Operations Shared Services",
            "Core Banking and Data Modernization",
            "Deposits and Relationship Growth",
            "Payments Franchise Expansion",
            "Third-party Spend Optimization",
            "Financial Crime Control Tower",
            "AI-enabled Contact Center",
        ),
        initiative_structures=BANK_STRUCTURES,
        initiative_value_factors=tuple(
            Decimal(value)
            for value in ("0.7", "1.4", "1.2", "1.1", "1.5", "1.3", "1.4", "1.0", "0.8", "1.2")
        ),
    ),
    CompanyProfile(
        name="Solstice Health Network",
        slug="qa-e2e-20260712-solstice-health-network",
        email_domain="solstice-health-network.transmuter.test",
        admin_display_name="Solstice Transformation Admin",
        admin_title="SVP, Transformation and Performance",
        currency="EUR",
        fiscal_start_month=1,
        baseline_revenue=Decimal("120000000"),
        baseline_gross_margin=Decimal("54000000"),
        value_scale=Decimal("6"),
        country="European Union",
        theme="Patient access, clinical capacity, and sustainable value",
        initiative_names=(
            "Health Transformation Value Office",
            "Patient Access Automation",
            "Revenue Cycle Excellence",
            "Clinical Workforce Productivity",
            "EHR and Health Data Modernization",
            "Ambulatory Network Growth",
            "Service Line Expansion",
            "Clinical Supply Chain Optimization",
            "Hospital Capacity Command Center",
            "Virtual Care Scale-up",
        ),
        initiative_structures=HEALTH_STRUCTURES,
        initiative_value_factors=tuple(
            Decimal(value)
            for value in ("0.7", "1.1", "1.2", "1.4", "1.3", "1.2", "1.0", "0.9", "1.4", "1.1")
        ),
    ),
    CompanyProfile(
        name="Horizon Energy & Utilities",
        slug="qa-e2e-20260712-horizon-energy-utilities",
        email_domain="horizon-energy-utilities.transmuter.test",
        admin_display_name="Horizon Transformation Admin",
        admin_title="Executive Director, Transformation",
        currency="AUD",
        fiscal_start_month=7,
        baseline_revenue=Decimal("300000000"),
        baseline_gross_margin=Decimal("135000000"),
        value_scale=Decimal("15"),
        country="Australia",
        theme="Reliable energy transition and asset productivity",
        initiative_names=(
            "Energy Transformation Value Office",
            "Digital Grid Automation",
            "Field Service Productivity",
            "Corporate Shared Services",
            "Asset Data Platform Modernization",
            "Customer Products and Retention Growth",
            "Renewable Connections Acceleration",
            "Strategic Sourcing and Contractor Optimization",
            "Network Operations Control Tower",
            "Predictive Asset Maintenance",
        ),
        initiative_structures=ENERGY_STRUCTURES,
        initiative_value_factors=tuple(
            Decimal(value)
            for value in ("0.8", "1.5", "1.2", "1.0", "1.4", "1.3", "1.1", "1.2", "1.4", "1.3")
        ),
    ),
)


def build_profile_initiative_rows(
    seed_rows: Sequence[InitiativeSeedRow],
    profile: CompanyProfile,
) -> tuple[InitiativeSeedRow, ...]:
    """Apply a company profile to the canonical 10-row enterprise seed."""
    if len(seed_rows) != 10:
        raise ValueError("Canonical enterprise seed must contain exactly 10 rows")
    codes = tuple(row[0] for row in seed_rows)
    if codes != _EXPECTED_CODES:
        raise ValueError("Canonical enterprise seed codes must be ENT-001 through ENT-010")

    result: list[InitiativeSeedRow] = []
    for row, initiative_name, structure, value_factor in zip(
        seed_rows,
        profile.initiative_names,
        profile.initiative_structures,
        profile.initiative_value_factors,
        strict=True,
    ):
        if len(row) != 16:
            raise ValueError("Canonical enterprise seed rows must contain 16 fields")
        financial_values = row[6:]
        if any(not isinstance(value, Decimal) for value in financial_values):
            raise TypeError("Canonical enterprise seed financial fields must use Decimal")
        scaled_baselines = tuple(value * profile.value_scale for value in financial_values[:2])
        scaled_values = tuple(
            value * profile.value_scale * value_factor for value in financial_values[2:]
        )
        result.append(
            cast(
                InitiativeSeedRow,
                (row[0], initiative_name, *structure, *scaled_baselines, *scaled_values),
            )
        )
    return tuple(result)
