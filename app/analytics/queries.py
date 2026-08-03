from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.analytics.models import AnalyticsDaily
from app.analytics.schemas import (
    AnalyticsFilters,
    AnalyticsOverviewResponse,
    FreshnessResponse,
    MetricResponse,
    PeriodResponse,
    TimeSeriesMetric,
    TimeSeriesPoint,
    TimeSeriesResponse,
)
from app.core.queries import BaseQuery, BaseQueryHandler
from app.core.services.auth.dto import UserJWTData
from app.marketplaces.models import SyncJob, SyncKind, SyncStatus
from app.organizations.exceptions import OrganizationForbiddenError
from app.organizations.services import OrganizationScopeService

METRIC_UNITS = {
    "orders_qty": "pcs",
    "sales_qty": "pcs",
    "returns_qty": "pcs",
    "buyout_rate": "%",
    "margin": "%",
    "drr": "%",
    "roi": "%",
    "ctr": "%",
    "conversion_rate": "%",
}


def _aggregate(rows: list[AnalyticsDaily]) -> tuple[dict[str, Decimal], set[str]]:
    metrics: dict[str, Decimal] = {}
    warnings: set[str] = set()
    for row in rows:
        for code, value in row.metrics.items():
            if value is not None:
                metrics[code] = metrics.get(code, Decimal("0")) + Decimal(str(value))
        for source, status in row.coverage.items():
            if status != "complete":
                warnings.add(f"{source.upper()}_DATA_{status.upper()}")
    return metrics, warnings


@dataclass(frozen=True)
class GetAnalyticsOverviewQuery(BaseQuery):
    user: UserJWTData
    filters: AnalyticsFilters


@dataclass(frozen=True)
class GetAnalyticsOverviewHandler(BaseQueryHandler[GetAnalyticsOverviewQuery, AnalyticsOverviewResponse]):
    session: AsyncSession
    scope_service: OrganizationScopeService

    async def handle(self, query: GetAnalyticsOverviewQuery) -> AnalyticsOverviewResponse:
        try:
            scope = await self.scope_service.require(
                int(query.user.id), query.filters.organization_id, "analytics:view"
            )
        except PermissionError as exc:
            raise OrganizationForbiddenError(permission="analytics:view") from exc
        requested = set(query.filters.cabinet_ids) or None
        allowed = scope.restrict_cabinets(requested)
        if allowed is not None and not allowed:
            raise OrganizationForbiddenError(permission="analytics:view")
        duration = (query.filters.date_to - query.filters.date_from).days + 1
        compare_to = query.filters.compare_date_to or query.filters.date_from - timedelta(days=1)
        compare_from = query.filters.compare_date_from or compare_to - timedelta(days=duration - 1)
        current_rows = await self._rows(
            query.filters.date_from, query.filters.date_to, query.filters.organization_id, allowed
        )
        previous_rows = await self._rows(compare_from, compare_to, query.filters.organization_id, allowed)
        current, warnings = _aggregate(current_rows)
        previous, _ = _aggregate(previous_rows)
        codes = sorted(set(current) | set(previous))
        metrics = []
        for code in codes:
            value = current.get(code)
            previous_value = previous.get(code)
            delta = value - previous_value if value is not None and previous_value is not None else None
            delta_percent = None
            if delta is not None and previous_value not in {None, Decimal("0")}:
                delta_percent = delta / previous_value * Decimal("100")
            metrics.append(
                MetricResponse(
                    code=code,
                    value=value,
                    unit=METRIC_UNITS.get(code, "RUB"),
                    previous_value=previous_value,
                    delta=delta,
                    delta_percent=delta_percent,
                    status="partial" if warnings else "complete",
                )
            )
        freshness = await self._freshness(query.filters.organization_id, allowed)
        return AnalyticsOverviewResponse(
            period=PeriodResponse(date_from=query.filters.date_from, date_to=query.filters.date_to),
            compare_period=PeriodResponse(date_from=compare_from, date_to=compare_to),
            metrics=metrics,
            data_freshness=freshness,
            warnings=sorted(warnings),
        )

    async def _rows(
        self,
        date_from: date,
        date_to: date,
        organization_id: UUID,
        allowed: frozenset[UUID] | None,
    ) -> list[AnalyticsDaily]:
        stmt = select(AnalyticsDaily).where(
            AnalyticsDaily.organization_id == organization_id,
            AnalyticsDaily.business_date.between(date_from, date_to),
        )
        if allowed is not None:
            stmt = stmt.where(AnalyticsDaily.cabinet_id.in_(allowed))
        return list((await self.session.scalars(stmt)).all())

    async def _freshness(
        self,
        organization_id: UUID,
        allowed: frozenset[UUID] | None,
    ) -> list[FreshnessResponse]:
        stmt = (
            select(SyncJob)
            .where(
                SyncJob.organization_id == organization_id,
                SyncJob.status == SyncStatus.SUCCEEDED,
            )
            .order_by(SyncJob.finished_at.desc())
        )
        if allowed is not None:
            stmt = stmt.where(SyncJob.cabinet_id.in_(allowed))
        jobs = list((await self.session.scalars(stmt)).all())
        by_cabinet: dict[UUID, SyncJob] = {}
        for job in jobs:
            by_cabinet.setdefault(job.cabinet_id, job)
        required = {SyncKind.ORDERS.value, SyncKind.SALES_RETURNS.value, SyncKind.FINANCE_TRANSACTIONS.value}
        return [
            FreshnessResponse(
                cabinet_id=cabinet_id,
                last_success_at=job.finished_at,
                complete_through=job.period_to,
                missing_kinds=sorted(required - {item.kind for item in jobs if item.cabinet_id == cabinet_id}),
            )
            for cabinet_id, job in by_cabinet.items()
        ]


@dataclass(frozen=True)
class GetAnalyticsTimeSeriesQuery(BaseQuery):
    user: UserJWTData
    filters: AnalyticsFilters


@dataclass(frozen=True)
class GetAnalyticsTimeSeriesHandler(BaseQueryHandler[GetAnalyticsTimeSeriesQuery, TimeSeriesResponse]):
    overview_handler: GetAnalyticsOverviewHandler

    async def handle(self, query: GetAnalyticsTimeSeriesQuery) -> TimeSeriesResponse:
        overview = await self.overview_handler.handle(GetAnalyticsOverviewQuery(user=query.user, filters=query.filters))
        scope = await self.overview_handler.scope_service.require(
            int(query.user.id), query.filters.organization_id, "analytics:view"
        )
        allowed = scope.restrict_cabinets(set(query.filters.cabinet_ids) or None)
        rows = await self.overview_handler._rows(
            query.filters.date_from, query.filters.date_to, query.filters.organization_id, allowed
        )
        grouped: dict[date, list[AnalyticsDaily]] = {}
        for row in rows:
            grouped.setdefault(row.business_date, []).append(row)
        return TimeSeriesResponse(
            period=overview.period,
            points=[
                TimeSeriesPoint(
                    business_date=day,
                    metrics=[
                        TimeSeriesMetric(code=code, value=value) for code, value in sorted(_aggregate(items)[0].items())
                    ],
                )
                for day, items in sorted(grouped.items())
            ],
            warnings=overview.warnings,
        )
