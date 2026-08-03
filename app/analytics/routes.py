from typing import Annotated
from uuid import UUID

from dishka import FromDishka
from dishka.integrations.fastapi import DishkaRoute
from fastapi import APIRouter, Query, status

from app.analytics.client_error_queries import ListClientErrorsQuery
from app.analytics.commands import RecordClientErrorCommand
from app.analytics.exports import CreateExportCommand, GetExportQuery
from app.analytics.queries import GetAnalyticsOverviewQuery, GetAnalyticsTimeSeriesQuery
from app.analytics.schemas import (
    AnalyticsFilters,
    AnalyticsOverviewResponse,
    ClientErrorRequest,
    ClientErrorResponse,
    ExportJobResponse,
    ExportRequest,
    TimeSeriesResponse,
)
from app.auth.deps import AuthCurrentUserJWTData
from app.core.db.repository import PageResult
from app.core.mediators.base import BaseMediator

router = APIRouter(tags=["analytics"], route_class=DishkaRoute)


@router.get("/analytics/overview")
async def overview(
    params: Annotated[AnalyticsFilters, Query()], mediator: FromDishka[BaseMediator], user: AuthCurrentUserJWTData
) -> AnalyticsOverviewResponse:
    return await mediator.handle_query(GetAnalyticsOverviewQuery(user=user, filters=params))


@router.get("/analytics/timeseries")
async def timeseries(
    params: Annotated[AnalyticsFilters, Query()], mediator: FromDishka[BaseMediator], user: AuthCurrentUserJWTData
) -> TimeSeriesResponse:
    return await mediator.handle_query(GetAnalyticsTimeSeriesQuery(user=user, filters=params))


@router.get("/analytics/products")
@router.get("/analytics/unit-economics")
@router.get("/analytics/advertising")
@router.get("/analytics/stocks")
@router.get("/analytics/plan-fact")
async def analytical_series(
    params: Annotated[AnalyticsFilters, Query()], mediator: FromDishka[BaseMediator], user: AuthCurrentUserJWTData
) -> TimeSeriesResponse:
    return await mediator.handle_query(GetAnalyticsTimeSeriesQuery(user=user, filters=params))


@router.post("/observability/client-errors", status_code=status.HTTP_201_CREATED)
async def record_client_error(
    request: ClientErrorRequest, mediator: FromDishka[BaseMediator], user: AuthCurrentUserJWTData
) -> ClientErrorResponse:
    return await mediator.handle_command(RecordClientErrorCommand(user=user, **request.model_dump()))


@router.get("/observability/client-errors")
async def list_client_errors(
    organization_id: UUID,
    mediator: FromDishka[BaseMediator],
    user: AuthCurrentUserJWTData,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> PageResult[ClientErrorResponse]:
    return await mediator.handle_query(
        ListClientErrorsQuery(user=user, organization_id=organization_id, page=page, page_size=page_size)
    )


@router.post("/exports", status_code=status.HTTP_202_ACCEPTED)
async def create_export(
    request: ExportRequest,
    mediator: FromDishka[BaseMediator],
    user: AuthCurrentUserJWTData,
) -> ExportJobResponse:
    return await mediator.handle_command(CreateExportCommand(user=user, filters=request.filters, format=request.format))


@router.get("/exports/{export_id}")
async def get_export(
    export_id: UUID,
    mediator: FromDishka[BaseMediator],
    user: AuthCurrentUserJWTData,
) -> ExportJobResponse:
    return await mediator.handle_query(GetExportQuery(user=user, export_id=export_id))
