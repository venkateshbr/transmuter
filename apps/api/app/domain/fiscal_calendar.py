"""Tenant fiscal-calendar primitives.

Persistence contract:
- integer ``year`` values are fiscal-year labels using the ending-year convention;
- integer ``month`` values are fiscal ordinals M01..M12;
- date values remain real Gregorian dates and are mapped at reporting boundaries.
"""

from __future__ import annotations

import re
from calendar import monthrange
from dataclasses import dataclass
from datetime import date, timedelta
from typing import Literal

FiscalGranularity = Literal["monthly", "quarterly", "yearly"]

_MONTHLY_PERIOD = re.compile(r"^(?P<year>\d{4})-M(?P<month>0[1-9]|1[0-2])$")
_QUARTERLY_PERIOD = re.compile(r"^(?P<year>\d{4})-Q(?P<quarter>[1-4])$")
_YEARLY_PERIOD = re.compile(r"^(?P<year>\d{4})$")


@dataclass(frozen=True, slots=True)
class FiscalPeriod:
    label: str
    year: int
    quarter: int | None = None
    month: int | None = None

    @classmethod
    def parse(cls, value: str, granularity: str) -> FiscalPeriod:
        patterns = {
            "monthly": _MONTHLY_PERIOD,
            "quarterly": _QUARTERLY_PERIOD,
            "yearly": _YEARLY_PERIOD,
        }
        pattern = patterns.get(granularity)
        if pattern is None:
            raise ValueError(f"Unsupported fiscal granularity: {granularity}")
        match = pattern.fullmatch(value)
        if not match:
            expected = {
                "monthly": "YYYY-M01..YYYY-M12",
                "quarterly": "YYYY-Q1..YYYY-Q4",
                "yearly": "YYYY",
            }[granularity]
            raise ValueError(f"Period must use canonical {granularity} form {expected}")
        year = int(match.group("year"))
        month = int(match.group("month")) if "month" in match.groupdict() else None
        quarter = int(match.group("quarter")) if "quarter" in match.groupdict() else None
        return cls(label=value, year=year, quarter=quarter, month=month)


@dataclass(frozen=True, slots=True)
class FiscalCalendar:
    start_month: int = 1

    def __post_init__(self) -> None:
        if not 1 <= self.start_month <= 12:
            raise ValueError("Fiscal year start month must be between 1 and 12")

    def year_bounds(self, fiscal_year: int) -> tuple[date, date]:
        start_year = fiscal_year if self.start_month == 1 else fiscal_year - 1
        start = date(start_year, self.start_month, 1)
        next_start = date(start_year + 1, self.start_month, 1)
        return start, next_start - timedelta(days=1)

    def fiscal_year_for_date(self, value: date) -> int:
        if self.start_month == 1:
            return value.year
        return value.year + 1 if value.month >= self.start_month else value.year

    def fiscal_month_for_date(self, value: date) -> int:
        return ((value.month - self.start_month) % 12) + 1

    def month_bounds(self, fiscal_year: int, fiscal_month: int) -> tuple[date, date]:
        if not 1 <= fiscal_month <= 12:
            raise ValueError("Fiscal month must be between 1 and 12")
        start_year = fiscal_year if self.start_month == 1 else fiscal_year - 1
        zero_based = (self.start_month - 1) + (fiscal_month - 1)
        calendar_year = start_year + (zero_based // 12)
        calendar_month = (zero_based % 12) + 1
        start = date(calendar_year, calendar_month, 1)
        return start, date(
            calendar_year, calendar_month, monthrange(calendar_year, calendar_month)[1]
        )

    def quarter_bounds(self, fiscal_year: int, fiscal_quarter: int) -> tuple[date, date]:
        if not 1 <= fiscal_quarter <= 4:
            raise ValueError("Fiscal quarter must be between 1 and 4")
        start, _ = self.month_bounds(fiscal_year, ((fiscal_quarter - 1) * 3) + 1)
        _, end = self.month_bounds(fiscal_year, fiscal_quarter * 3)
        return start, end

    def period_for_date(self, value: date, granularity: FiscalGranularity) -> FiscalPeriod:
        fiscal_year = self.fiscal_year_for_date(value)
        fiscal_month = self.fiscal_month_for_date(value)
        if granularity == "monthly":
            return FiscalPeriod(
                label=f"{fiscal_year}-M{fiscal_month:02d}",
                year=fiscal_year,
                month=fiscal_month,
            )
        if granularity == "quarterly":
            quarter = ((fiscal_month - 1) // 3) + 1
            return FiscalPeriod(
                label=f"{fiscal_year}-Q{quarter}", year=fiscal_year, quarter=quarter
            )
        return FiscalPeriod(label=str(fiscal_year), year=fiscal_year)

    def week_for_date(self, value: date) -> tuple[int, int]:
        fiscal_year = self.fiscal_year_for_date(value)
        start, _ = self.year_bounds(fiscal_year)
        return fiscal_year, ((value - start).days // 7) + 1
