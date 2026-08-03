from typing import Annotated
from uuid import UUID

from dishka import FromDishka
from dishka.integrations.fastapi import DishkaRoute
from fastapi import APIRouter, Query, Response, status

from app.auth.deps import AuthCurrentUserJWTData
from app.core.db.repository import PageResult
from app.core.mediators.base import BaseMediator
from app.marketplaces.commands import (
    CreateCabinetCommand,
    DeleteCabinetCommand,
    RetrySyncCommand,
    StartSyncCommand,
    UpdateCabinetCommand,
    ValidateCredentialCommand,
)
from app.marketplaces.queries import (
    GetCabinetQuery,
    GetSyncJobQuery,
    GetSyncOverviewQuery,
    ListCabinetsQuery,
    ListSyncJobsQuery,
)
from app.marketplaces.schemas import (
    CabinetCreateRequest,
    CabinetResponse,
    CabinetUpdateRequest,
    CredentialValidateRequest,
    CredentialValidationResponse,
    SyncJobResponse,
    SyncOverviewResponse,
    SyncStartRequest,
    SyncStartResponse,
)

router = APIRouter(tags=["marketplaces"], route_class=DishkaRoute)


@router.get("/cabinets")
async def list_cabinets(
    mediator: FromDishka[BaseMediator],
    user: AuthCurrentUserJWTData,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
    marketplace: str | None = None,
) -> PageResult[CabinetResponse]:
    return await mediator.handle_query(
        ListCabinetsQuery(user=user, page=page, page_size=page_size, marketplace=marketplace)
    )


@router.post("/cabinets", status_code=status.HTTP_201_CREATED)
async def create_cabinet(
    request: CabinetCreateRequest, mediator: FromDishka[BaseMediator], user: AuthCurrentUserJWTData
) -> CabinetResponse:
    return await mediator.handle_command(CreateCabinetCommand(user=user, **request.model_dump()))


@router.get("/cabinets/{cabinet_id}")
async def get_cabinet(
    cabinet_id: UUID, mediator: FromDishka[BaseMediator], user: AuthCurrentUserJWTData
) -> CabinetResponse:
    return await mediator.handle_query(GetCabinetQuery(user=user, cabinet_id=cabinet_id))


@router.patch("/cabinets/{cabinet_id}")
async def update_cabinet(
    cabinet_id: UUID, request: CabinetUpdateRequest, mediator: FromDishka[BaseMediator], user: AuthCurrentUserJWTData
) -> CabinetResponse:
    return await mediator.handle_command(UpdateCabinetCommand(user=user, cabinet_id=cabinet_id, **request.model_dump()))


@router.delete("/cabinets/{cabinet_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_cabinet(
    cabinet_id: UUID, mediator: FromDishka[BaseMediator], user: AuthCurrentUserJWTData
) -> Response:
    await mediator.handle_command(DeleteCabinetCommand(user=user, cabinet_id=cabinet_id))
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/cabinets/{cabinet_id}/credentials/validate")
async def validate_credential(
    cabinet_id: UUID,
    request: CredentialValidateRequest,
    mediator: FromDishka[BaseMediator],
    user: AuthCurrentUserJWTData,
) -> CredentialValidationResponse:
    return await mediator.handle_command(
        ValidateCredentialCommand(user=user, cabinet_id=cabinet_id, new_credential=request.credential)
    )


@router.post("/cabinets/{cabinet_id}/sync", status_code=status.HTTP_202_ACCEPTED)
async def start_sync(
    cabinet_id: UUID, request: SyncStartRequest, mediator: FromDishka[BaseMediator], user: AuthCurrentUserJWTData
) -> SyncStartResponse:
    return await mediator.handle_command(
        StartSyncCommand(
            user=user,
            cabinet_id=cabinet_id,
            kinds=frozenset(request.kinds),
            date_from=request.date_from,
            date_to=request.date_to,
        )
    )


@router.get("/cabinets/{cabinet_id}/sync-jobs")
async def list_sync_jobs(
    cabinet_id: UUID,
    mediator: FromDishka[BaseMediator],
    user: AuthCurrentUserJWTData,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> PageResult[SyncJobResponse]:
    return await mediator.handle_query(
        ListSyncJobsQuery(user=user, cabinet_id=cabinet_id, page=page, page_size=page_size)
    )


@router.get("/sync-jobs/{job_id}")
async def get_sync_job(
    job_id: UUID, mediator: FromDishka[BaseMediator], user: AuthCurrentUserJWTData
) -> SyncJobResponse:
    return await mediator.handle_query(GetSyncJobQuery(user=user, job_id=job_id))


@router.post("/sync-jobs/{job_id}/retry")
async def retry_sync_job(
    job_id: UUID, mediator: FromDishka[BaseMediator], user: AuthCurrentUserJWTData
) -> SyncJobResponse:
    return await mediator.handle_command(RetrySyncCommand(user=user, job_id=job_id))


@router.get("/sync/overview")
async def sync_overview(mediator: FromDishka[BaseMediator], user: AuthCurrentUserJWTData) -> SyncOverviewResponse:
    return await mediator.handle_query(GetSyncOverviewQuery(user=user))
