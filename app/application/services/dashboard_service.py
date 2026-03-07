# app/application/services/dashboard_service.py
from __future__ import annotations

import asyncio
from datetime import date, datetime, timezone
from typing import Optional
from typing import Optional, Literal, TypedDict
from app.infrastructure.repositories.dashboard_analytics_sqlalchemy import DashboardRepository
from app.presentation.schemas.analytics_schema import (
    DashboardSummaryOut,
    EntitySummaryOut,
    PeriodOut,
)


# ---------------------------
# Date helpers
# ---------------------------

def month_start(d: date) -> date:
    """Return the first day of the month for the given date."""
    return date(d.year, d.month, 1)


def next_month_start(d: date) -> date:
    """Return the first day of the next month for the given month's start date."""
    return date(d.year + 1, 1, 1) if d.month == 12 else date(d.year, d.month + 1, 1)


def prev_month_start(d: date) -> date:
    """Return the first day of the previous month for the given month's start date."""
    return date(d.year - 1, 12, 1) if d.month == 1 else date(d.year, d.month - 1, 1)


def pct_change(curr: int, prev: int, round_to: Optional[int] = 2) -> Optional[float]:
    """
    Compute percentage change between current and previous values.
    Returns None when previous == 0 to avoid division by zero.
    """
    if prev == 0:
        return None
    pct = ((curr - prev) / prev) * 100.0
    return round(pct, round_to) if round_to is not None else pct


# ---------------------------
# Service
# ---------------------------

Trend = Literal['up', 'down', 'flat']


# ---------- Date helpers ----------
def month_start(d: date) -> date:
    return date(d.year, d.month, 1)


def next_month_start(d: date) -> date:
    return date(d.year + 1, 1, 1) if d.month == 12 else date(d.year, d.month + 1, 1)


def prev_month_start(d: date) -> date:
    return date(d.year - 1, 12, 1) if d.month == 1 else date(d.year, d.month - 1, 1)


# ---------- MoM logic (per your rules) ----------
def mom_values(
        curr: int,
        prev: int,
        *,
        round_to: int = 1,
        flat_as_up: bool = False
) -> Tuple[Optional[float], Trend, str]:
    """
    Returns (change_pct, trend, change_label)

    Rules:
      - If prev > 0: pct = ((curr - prev)/prev)*100 (rounded), trend by sign, label e.g. "+25.0%"
      - If prev == 0 and curr > 0: pct=None (undefined/infinite), trend='up', label="NEW"
      - If prev == 0 and curr == 0: pct=0.0, trend='flat' (or 'up' if flat_as_up), label="0%"
    """
    if prev > 0:
        pct = ((curr - prev) / prev) * 100.0
        pct_rounded = round(pct, round_to)
        if curr > prev:
            trend: Trend = 'up'
        elif curr < prev:
            trend = 'down'
        else:
            trend = 'up' if flat_as_up else 'flat'
            pct_rounded = 0.0
        sign = '+' if pct_rounded > 0 else ''
        label = f"{sign}{pct_rounded:.{round_to}f}%"
        return pct_rounded, trend, label

    # prev == 0
    if curr > 0:
        # Infinite/undefined growth
        return None, 'up', "NEW"
    # curr == 0 and prev == 0
    return 0.0, ('up' if flat_as_up else 'flat'), "0%"


class DashboardService:
    """
    Provides dashboard summary:
      - total active counts for portfolios, programs, projects, users
      - current vs previous month creations and changes (pct, trend, label)
    """

    def __init__(self, repo: DashboardRepository) -> None:
        self.repo = repo

    async def get_summary(
            self,
            *,
            today: Optional[date] = None,
            round_pct_to: int = 1,
            flat_as_up: bool = False,
    ) -> DashboardSummaryOut:
        """
        Build the dashboard summary payload.

        Args:
            today: override "today" (UTC date). Defaults to now().
            round_pct_to: decimals for percent rounding (default 1).
            flat_as_up: show 'up' when curr == prev (non-standard, default False).
        """
        # Determine period boundaries (UTC-based)
        today = today or datetime.now(timezone.utc).date()
        cur_start = month_start(today)
        cur_end = next_month_start(cur_start)
        prev_start = prev_month_start(cur_start)
        prev_end = cur_start

        # Totals (active) fetched concurrently
        (
            portfolios_total,
            programs_total,
            projects_total,
            users_total,
        ) = await asyncio.gather(
            self.repo.total_active_portfolios(),
            self.repo.total_active_programs(),
            self.repo.total_active_projects(),
            self.repo.total_active_users(),
        )

        # Creations current / previous fetched concurrently
        (
            p_cur, p_prev,
            g_cur, g_prev,
            j_cur, j_prev,
            u_cur, u_prev,
        ) = await asyncio.gather(
            self.repo.created_portfolios(cur_start, cur_end),
            self.repo.created_portfolios(prev_start, prev_end),
            self.repo.created_programs(cur_start, cur_end),
            self.repo.created_programs(prev_start, prev_end),
            self.repo.created_projects(cur_start, cur_end),
            self.repo.created_projects(prev_start, prev_end),
            self.repo.created_users(cur_start, cur_end),
            self.repo.created_users(prev_start, prev_end),
        )

        # Compute MoM per entity
        p_pct, p_trend, p_label = mom_values(p_cur, p_prev, round_to=round_pct_to, flat_as_up=flat_as_up)
        g_pct, g_trend, g_label = mom_values(g_cur, g_prev, round_to=round_pct_to, flat_as_up=flat_as_up)
        j_pct, j_trend, j_label = mom_values(j_cur, j_prev, round_to=round_pct_to, flat_as_up=flat_as_up)
        u_pct, u_trend, u_label = mom_values(u_cur, u_prev, round_to=round_pct_to, flat_as_up=flat_as_up)

        return DashboardSummaryOut(
            as_of=datetime.now(timezone.utc),
            period=PeriodOut(
                current_month_start=cur_start,
                previous_month_start=prev_start,
            ),
            portfolios=EntitySummaryOut(
                total_active=portfolios_total,
                current_month=p_cur,
                previous_month=p_prev,
                change_pct=p_pct,
                trend=p_trend,
                change_label=p_label,
            ),
            programs=EntitySummaryOut(
                total_active=programs_total,
                current_month=g_cur,
                previous_month=g_prev,
                change_pct=g_pct,
                trend=g_trend,
                change_label=g_label,
            ),
            projects=EntitySummaryOut(
                total_active=projects_total,
                current_month=j_cur,
                previous_month=j_prev,
                change_pct=j_pct,
                trend=j_trend,
                change_label=j_label,
            ),
            users=EntitySummaryOut(
                total_active=users_total,
                current_month=u_cur,
                previous_month=u_prev,
                change_pct=u_pct,
                trend=u_trend,
                change_label=u_label,
            ),
        )
