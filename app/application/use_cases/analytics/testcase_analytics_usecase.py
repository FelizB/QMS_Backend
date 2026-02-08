from typing import Optional

from app.application.services.case_rules import RulesService
from app.infrastructure.repositories.testcase_analytics_repository_sqlalchemy import AnalyticsRepository
from app.infrastructure.repositories.testcase_next_analytics_repository_sqlalchemy import AnalyticsNextRepository


class GetTestCaseSummary:
    def __init__(self, session):
        self.repo = AnalyticsRepository(session)
        self.rules = RulesService(session)

    async def __call__(self, project_id: int, release_id: Optional[int]):
        await self.rules.ensure_project_chain_active(project_id)
        total = await self.repo.test_case_total(project_id, release_id)
        by_status = await self.repo.test_case_counts_by_status(project_id, release_id)
        by_type = await self.repo.test_case_counts_by_type(project_id, release_id)
        by_priority = await self.repo.test_case_counts_by_priority(project_id, release_id)
        return {"by_status": by_status, "by_type": by_type, "by_priority": by_priority, "total": total}


class GetStepExecutionSummary:
    def __init__(self, session):
        self.repo = AnalyticsRepository(session)
        self.rules = RulesService(session)

    async def __call__(self, project_id: int, release_id: Optional[int]):
        await self.rules.ensure_project_chain_active(project_id)
        items = await self.repo.step_execution_summary_per_case(project_id, release_id)
        return {"items": items}


class GetTestCaseTrends:
    def __init__(self, session):
        self.repo = AnalyticsRepository(session)
        self.rules = RulesService(session)

    async def __call__(self, project_id: int, period: str, date_from: Optional[str], date_to: Optional[str]):
        await self.rules.ensure_project_chain_active(project_id)
        series, total = await self.repo.trends_created(project_id, period, date_from, date_to)
        return {"period": period, "series": series, "total": total}


class GetTestCaseAging:
    def __init__(self, session):
        self.repo = AnalyticsRepository(session)
        self.rules = RulesService(session)

    async def __call__(self, project_id: int, days_without_update: int, not_run_id: Optional[int] = 0):
        await self.rules.ensure_project_chain_active(project_id)
        never_executed, stale = await self.repo.aging(project_id, days_without_update, not_run_id)
        return {"never_executed": never_executed, "stale": stale, "threshold_days": days_without_update}


class GetCoverage:
    def __init__(self, session):
        self.repo = AnalyticsNextRepository(session)
        self.rules = RulesService(session)

    async def __call__(self, project_id: int, release_id: Optional[int], not_run_id: Optional[int]):
        await self.rules.ensure_project_chain_active(project_id)
        total, executed, not_exec = await self.repo.coverage(project_id, release_id, not_run_id)
        executed_pct = round((executed * 100.0 / total), 2) if total > 0 else 0.0
        return {
            "total_cases": total,
            "executed_cases": executed,
            "not_executed_cases": not_exec,
            "executed_pct": executed_pct,
        }


class GetFolderBreakdown:
    def __init__(self, session):
        self.repo = AnalyticsNextRepository(session)
        self.rules = RulesService(session)

    async def __call__(self, project_id: int, release_id: Optional[int]):
        await self.rules.ensure_project_chain_active(project_id)
        rows, total = await self.repo.folder_breakdown(project_id, release_id)
        return {"items": [{"folder_id": fid, "count": cnt} for fid, cnt in rows], "total": total}


class GetStepTrend:
    def __init__(self, session):
        self.repo = AnalyticsNextRepository(session)
        self.rules = RulesService(session)

    async def __call__(self, project_id: int, release_id: Optional[int], period: str, date_from: Optional[str],
                       date_to: Optional[str]):
        await self.rules.ensure_project_chain_active(project_id)
        rows, total_steps, names = await self.repo.step_execution_trend(project_id, release_id, period, date_from,
                                                                        date_to)
        series = [
            {"period": dt.date().isoformat(), "status_id": int(sid), "status_name": names.get(sid), "count": int(cnt)}
            for dt, sid, cnt in rows]
        return {"period": period, "series": series, "total_steps": total_steps}


class GetHealthcard:
    def __init__(self, session):
        self.repo = AnalyticsNextRepository(session)
        self.rules = RulesService(session)

    async def __call__(self, project_id: int, release_id: Optional[int], passed_status_id: Optional[int],
                       not_run_id: Optional[int]):
        await self.rules.ensure_project_chain_active(project_id)

        # Summary by status/type/priority
        total = await self.repo.test_case_total(project_id, release_id)
        status_counts = await self.repo.counts_by_fk(project_id, release_id, "test_case_status_id")
        type_counts = await self.repo.counts_by_fk(project_id, release_id, "test_case_type_id")
        prio_counts = await self.repo.counts_by_fk(project_id, release_id, "priority_id")
        status_names, type_names, prio_names = await self.repo.lookup_names()

        summary = {
            "by_status": [{"id": _id, "name": status_names.get(_id), "count": cnt} for _id, cnt in status_counts],
            "by_type": [{"id": _id, "name": type_names.get(_id), "count": cnt} for _id, cnt in type_counts],
            "by_priority": [{"id": _id, "name": prio_names.get(_id), "count": cnt} for _id, cnt in prio_counts],
            "total": total,
        }

        # Steps overview
        rows, total_steps, exec_names = await self.repo.step_overview(project_id, release_id)
        totals = [{"status_id": sid, "status_name": exec_names.get(sid), "count": int(cnt)} for sid, cnt in rows]
        pass_rate = None
        if passed_status_id is not None and total_steps > 0:
            passed = next((int(c) for sid, c in rows if sid == passed_status_id), 0)
            pass_rate = round((passed * 100.0 / total_steps), 2)
        steps_overview = {"totals": totals, "total_steps": total_steps, "pass_rate": pass_rate}

        # Coverage
        cov = await GetCoverage(self.repo.session)(project_id, release_id, not_run_id)

        return {"summary": summary, "steps_overview": steps_overview, "coverage": cov}
