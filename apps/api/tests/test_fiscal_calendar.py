from datetime import date

import pytest
from fastapi import HTTPException

from app.domain.fiscal_calendar import FiscalCalendar, FiscalPeriod
from app.services.executive_control import ExecutiveControlService
from app.services.financial import FinancialService


@pytest.mark.parametrize(
    ("start_month", "fiscal_year", "expected_start", "expected_end"),
    [
        (1, 2028, date(2028, 1, 1), date(2028, 12, 31)),
        (4, 2028, date(2027, 4, 1), date(2028, 3, 31)),
        (7, 2028, date(2027, 7, 1), date(2028, 6, 30)),
    ],
)
def test_fiscal_year_uses_ending_year_contract(
    start_month: int,
    fiscal_year: int,
    expected_start: date,
    expected_end: date,
) -> None:
    calendar = FiscalCalendar(start_month)

    assert calendar.year_bounds(fiscal_year) == (expected_start, expected_end)
    assert calendar.fiscal_year_for_date(expected_start) == fiscal_year
    assert calendar.fiscal_year_for_date(expected_end) == fiscal_year


def test_fiscal_month_and_quarter_are_ordinal_within_fiscal_year() -> None:
    calendar = FiscalCalendar(4)

    assert calendar.period_for_date(date(2027, 4, 1), "monthly") == FiscalPeriod(
        label="2028-M01", year=2028, month=1
    )
    assert calendar.period_for_date(date(2027, 12, 31), "quarterly") == FiscalPeriod(
        label="2028-Q3", year=2028, quarter=3
    )
    assert calendar.month_bounds(2028, 12) == (date(2028, 3, 1), date(2028, 3, 31))


@pytest.mark.parametrize(
    ("period", "granularity"),
    [
        ("2028-01", "monthly"),
        ("2028-M13", "monthly"),
        ("2028-Q5", "quarterly"),
        ("2028-Q1", "monthly"),
        ("2028", "quarterly"),
    ],
)
def test_period_parser_rejects_noncanonical_or_mismatched_values(
    period: str, granularity: str
) -> None:
    with pytest.raises(ValueError):
        FiscalPeriod.parse(period, granularity)


def test_period_parser_accepts_canonical_values() -> None:
    assert FiscalPeriod.parse("2028-M01", "monthly") == FiscalPeriod(
        label="2028-M01", year=2028, month=1
    )
    assert FiscalPeriod.parse("2028-Q4", "quarterly") == FiscalPeriod(
        label="2028-Q4", year=2028, quarter=4
    )
    assert FiscalPeriod.parse("2028", "yearly") == FiscalPeriod(label="2028", year=2028)


class _AprilReportingRepo:
    @staticmethod
    def get_reporting_settings() -> dict[str, object]:
        return {"fiscal_year_start_month": 4, "reporting_currency": "GBP"}

    @staticmethod
    def get_organization_settings() -> dict[str, object]:
        return {}

    @staticmethod
    def get_financial_reporting_settings() -> dict[str, object]:
        return {"fiscal_year_start_month": 4, "reporting_currency": "GBP"}


def test_financial_service_rejects_noncanonical_contributor_period_with_422() -> None:
    service = FinancialService.__new__(FinancialService)
    service._repo = _AprilReportingRepo()

    with pytest.raises(HTTPException) as exc:
        service._parse_portfolio_period("2028-01", "monthly")

    assert exc.value.status_code == 422
    assert "YYYY-M01" in str(exc.value.detail)


def test_benefit_ledger_dates_group_into_tenant_fiscal_periods() -> None:
    service = FinancialService.__new__(FinancialService)
    service._repo = _AprilReportingRepo()

    assert service._benefit_period_key(date(2027, 4, 1), "monthly") == (2028, None, 1)
    assert service._benefit_period_key(date(2028, 3, 31), "yearly") == (2028, None, None)


def test_shared_cost_period_bounds_and_allocation_year_use_fiscal_calendar() -> None:
    service = ExecutiveControlService.__new__(ExecutiveControlService)
    service._repo = _AprilReportingRepo()

    assert service._period_bounds({"year": 2028, "quarter": 1}) == (
        date(2027, 4, 1),
        date(2027, 6, 30),
    )
    assert (
        service._allocation_year({"shared_cost_allocation_runs": {"period_start": "2027-04-01"}}, 4)
        == 2028
    )

    payload = service._period_payload({"year": 2028, "quarter": 4})
    assert payload["period_start"] == "2028-01-01"
    assert payload["period_end"] == "2028-03-31"


def test_bankable_snapshot_period_matching_uses_fiscal_year_and_month_ordinals() -> None:
    service = FinancialService.__new__(FinancialService)
    service._repo = _AprilReportingRepo()

    row = {"year": 2028, "month": 1}
    assert service._ledger_row_matches_period(row, "monthly", date(2027, 4, 1))
    assert not service._ledger_row_matches_period(row, "monthly", date(2028, 4, 1))
