"""Fiscal-year configuration and helpers.

Most Odoo installations use a calendar fiscal year (Jan-Dec) but many
real enterprises use Apr-Mar or Jul-Jun. Keep this configurable so the
temporal parser maps "fiscal Q3" correctly per tenant.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class FiscalConfig:
    """Fiscal calendar configuration.

    ``fiscal_year_start_month`` is the 1-indexed month the fiscal year
    *begins* (e.g. 4 = April for an April-March fiscal year).
    """

    fiscal_year_start_month: int = 1
    fiscal_year_start_day: int = 1

    @property
    def is_calendar_year(self) -> bool:
        return (
            self.fiscal_year_start_month == 1
            and self.fiscal_year_start_day == 1
        )

    def fiscal_year_for(self, d: date) -> int:
        """Return the fiscal year that contains ``d``.

        Convention: the FY label equals the calendar year in which the FY
        *ends*. So for an Apr-Mar fiscal year:
            2026-03-31 → FY 2026
            2026-04-01 → FY 2027
        For a calendar fiscal year both equal the calendar year.
        """
        if self.is_calendar_year:
            return d.year
        starts = date(d.year, self.fiscal_year_start_month, self.fiscal_year_start_day)
        if d >= starts:
            return d.year + 1
        return d.year

    def fiscal_year_bounds(self, fy: int) -> tuple[date, date]:
        """Return [start, end_exclusive) of fiscal year ``fy``."""
        if self.is_calendar_year:
            return date(fy, 1, 1), date(fy + 1, 1, 1)
        start = date(
            fy - 1,
            self.fiscal_year_start_month,
            self.fiscal_year_start_day,
        )
        end = date(
            fy,
            self.fiscal_year_start_month,
            self.fiscal_year_start_day,
        )
        return start, end

    def fiscal_quarter_bounds(self, fy: int, q: int) -> tuple[date, date]:
        """Return [start, end_exclusive) of fiscal quarter ``q`` of FY ``fy``."""
        if not 1 <= q <= 4:
            raise ValueError(f"Quarter must be 1..4, got {q}")
        fy_start, _ = self.fiscal_year_bounds(fy)
        # Month-arithmetic without dateutil to keep this dependency-free.
        start_month = ((fy_start.month - 1 + (q - 1) * 3) % 12) + 1
        start_year = fy_start.year + ((fy_start.month - 1 + (q - 1) * 3) // 12)
        end_month = ((fy_start.month - 1 + q * 3) % 12) + 1
        end_year = fy_start.year + ((fy_start.month - 1 + q * 3) // 12)
        return date(start_year, start_month, 1), date(end_year, end_month, 1)
