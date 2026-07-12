from __future__ import annotations

from dataclasses import FrozenInstanceError
from decimal import Decimal
from typing import cast

import pytest

from scripts.multi_tenant_transformation_profiles import (
    COMPANY_PROFILES,
    CompanyProfile,
    InitiativeSeedRow,
    build_profile_initiative_rows,
)


def _seed_rows() -> tuple[InitiativeSeedRow, ...]:
    rows: list[InitiativeSeedRow] = []
    for index in range(1, 11):
        financial_values = tuple(Decimal(index * 100 + offset) for offset in range(10))
        rows.append(
            cast(
                InitiativeSeedRow,
                (
                    f"ENT-{index:03d}",
                    f"Canonical initiative {index}",
                    f"Business unit {index}",
                    f"Workstream {index}",
                    "automation",
                    "cost_reduction",
                    *financial_values,
                ),
            )
        )
    return tuple(rows)


def test_company_profiles_define_five_unique_valid_companies() -> None:
    assert [profile.name for profile in COMPANY_PROFILES] == [
        "Acme Global Manufacturing",
        "Northstar Retail Group",
        "Meridian Commercial Bank",
        "Solstice Health Network",
        "Horizon Energy & Utilities",
    ]
    assert len({profile.slug for profile in COMPANY_PROFILES}) == 5
    assert len({profile.email_domain for profile in COMPANY_PROFILES}) == 5
    assert all(profile.slug.startswith("qa-e2e-20260712-") for profile in COMPANY_PROFILES)

    supported_currencies = {"AUD", "EUR", "GBP", "SGD", "USD"}
    for profile in COMPANY_PROFILES:
        assert len(profile.initiative_names) == 10
        assert len(set(profile.initiative_names)) == 10
        assert len(profile.initiative_structures) == 10
        assert len(profile.initiative_value_factors) == 10
        assert profile.email_domain.endswith(".transmuter.test")
        assert "@" not in profile.email_domain
        assert profile.currency in supported_currencies
        assert 1 <= profile.fiscal_start_month <= 12
        assert isinstance(profile.baseline_revenue, Decimal)
        assert isinstance(profile.baseline_gross_margin, Decimal)
        assert isinstance(profile.value_scale, Decimal)
        assert profile.baseline_revenue == Decimal("20000000") * profile.value_scale
        assert profile.baseline_gross_margin == Decimal("9000000") * profile.value_scale


def test_company_profile_is_immutable() -> None:
    with pytest.raises(FrozenInstanceError):
        COMPANY_PROFILES[0].name = "Changed"  # type: ignore[misc]


@pytest.mark.parametrize("profile", COMPANY_PROFILES, ids=lambda profile: profile.slug)
def test_build_profile_initiative_rows_replaces_names_and_scales_decimals(
    profile: CompanyProfile,
) -> None:
    seed_rows = _seed_rows()

    result = build_profile_initiative_rows(list(seed_rows), profile)

    assert len(result) == 10
    assert tuple(row[0] for row in result) == tuple(f"ENT-{index:03d}" for index in range(1, 11))
    assert tuple(row[1] for row in result) == profile.initiative_names
    for index, (source, scaled) in enumerate(zip(seed_rows, result, strict=True)):
        assert scaled[2:6] == profile.initiative_structures[index]
        assert scaled[6:8] == tuple(value * profile.value_scale for value in source[6:8])
        assert scaled[8:] == tuple(
            value * profile.value_scale * profile.initiative_value_factors[index]
            for value in source[8:]
        )
        assert all(isinstance(value, Decimal) for value in scaled[6:])
    assert seed_rows == _seed_rows()


def test_build_profile_initiative_rows_rejects_noncanonical_input() -> None:
    profile = COMPANY_PROFILES[0]
    seed_rows = _seed_rows()

    with pytest.raises(ValueError, match="exactly 10"):
        build_profile_initiative_rows(seed_rows[:-1], profile)

    wrong_code = cast(InitiativeSeedRow, ("BAD-001", *seed_rows[0][1:]))
    with pytest.raises(ValueError, match="ENT-001 through ENT-010"):
        build_profile_initiative_rows((wrong_code, *seed_rows[1:]), profile)

    non_decimal = cast(InitiativeSeedRow, (*seed_rows[0][:6], 1, *seed_rows[0][7:]))
    with pytest.raises(TypeError, match="must use Decimal"):
        build_profile_initiative_rows((non_decimal, *seed_rows[1:]), profile)
