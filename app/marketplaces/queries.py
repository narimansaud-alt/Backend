from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import func, select

from app.core.db.repository import PageResult
from app.core.filters.pagination import Pagination
from app.core.queries import BaseQuery, BaseQueryHandler
from app.core.services.auth.dto import UserJWTData
from app.marketplaces.commands import _require_cabinet
from app.marketplaces.exceptions import CabinetNotFoundError
from app.marketplaces.filters import CabinetFilter, SyncJobFilter
from app.marketplaces.models import MarketplaceCabinet, SyncJob, SyncStatus
from app.marketplaces.repositories import CabinetRepository, SyncJobRepository, get_credential
from app.marketplaces.schemas import CabinetResponse, SyncJobResponse, SyncOverviewResponse
from app.organizations.models import MemberCabinetAccess, OrganizationMember, OrganizationRole
from app.organizations.services import OrganizationScopeService


@dataclass(frozen=True)
class ListCabinetsQuery(BaseQuery):
    user: UserJWTData
    page: int
    page_size: int
    marketplace: str | None = None


@dataclass(frozen=True)
class ListCabinetsHandler(BaseQueryHandler[ListCabinetsQuery, PageResult[CabinetResponse]]):
    repository: CabinetRepository

    async def handle(self, query: ListCabinetsQuery) -> PageResult[CabinetResponse]:
        user_id = int(query.user.id)
        member_rows = (
            (
                await self.repository.session.execute(
                    select(OrganizationMember).where(
                        OrganizationMember.user_id == user_id,
                        OrganizationMember.is_active.is_(True),
                    )
                )
            )
            .scalars()
            .all()
        )
        unrestricted_orgs = [
            m.organization_id for m in member_rows if m.role in {OrganizationRole.OWNER, OrganizationRole.ADMIN}
        ]
        restricted_members = [
            m.id for m in member_rows if m.role in {OrganizationRole.MANAGER, OrganizationRole.VIEWER}
        ]
        assigned = []
        if restricted_members:
            assigned = list(
                (
                    await self.repository.session.scalars(
                        select(MemberCabinetAccess.cabinet_id).where(
                            MemberCabinetAccess.member_id.in_(restricted_members)
                        )
                    )
                ).all()
            )
        filters = CabinetFilter(
            organization_ids=unrestricted_orgs or None,
            cabinet_ids=assigned or None,
            marketplace=query.marketplace,
        )
        filters.set_pagination(Pagination(query.page, query.page_size))
        if not unrestricted_orgs and not assigned:
            return PageResult(items=[], total=0, page=query.page, page_size=query.page_size)
        # A mixed unrestricted/restricted scope needs OR semantics, so query it explicitly.
        if unrestricted_orgs and assigned:
            stmt = MarketplaceCabinet.select_not_deleted().where(
                MarketplaceCabinet.is_active.is_(True),
                (MarketplaceCabinet.organization_id.in_(unrestricted_orgs)) | (MarketplaceCabinet.id.in_(assigned)),
            )
            if query.marketplace:
                stmt = stmt.where(MarketplaceCabinet.marketplace == query.marketplace)
            total = await self.repository.session.scalar(select(func.count()).select_from(stmt.subquery())) or 0
            rows = (
                await self.repository.session.scalars(
                    stmt.offset(filters.pagination.offset).limit(filters.pagination.limit)
                )
            ).all()
            result = PageResult(items=list(rows), total=total, page=query.page, page_size=query.page_size)
        else:
            result = await self.repository.find_by_filter(MarketplaceCabinet, filters)
        items: list[CabinetResponse] = []
        for cabinet in result.items:
            credential = await get_credential(self.repository.session, cabinet.id)
            response = CabinetResponse.model_validate(cabinet)
            if credential:
                response = response.model_copy(
                    update={
                        "credential_masked_hint": credential.masked_hint,
                        "credential_scopes": credential.scopes,
                        "credential_validated_at": credential.validated_at,
                    }
                )
            items.append(response)
        return PageResult(items=items, total=result.total, page=result.page, page_size=result.page_size)


@dataclass(frozen=True)
class GetCabinetQuery(BaseQuery):
    user: UserJWTData
    cabinet_id: UUID


@dataclass(frozen=True)
class GetCabinetHandler(BaseQueryHandler[GetCabinetQuery, CabinetResponse]):
    repository: CabinetRepository
    scope_service: OrganizationScopeService

    async def handle(self, query: GetCabinetQuery) -> CabinetResponse:
        cabinet = await _require_cabinet(
            query.cabinet_id, query.user, "cabinet:view", self.repository, self.scope_service
        )
        credential = await get_credential(self.repository.session, cabinet.id)
        response = CabinetResponse.model_validate(cabinet)
        if credential:
            response = response.model_copy(
                update={
                    "credential_masked_hint": credential.masked_hint,
                    "credential_scopes": credential.scopes,
                    "credential_validated_at": credential.validated_at,
                }
            )
        return response


@dataclass(frozen=True)
class ListSyncJobsQuery(BaseQuery):
    user: UserJWTData
    cabinet_id: UUID
    page: int
    page_size: int


@dataclass(frozen=True)
class ListSyncJobsHandler(BaseQueryHandler[ListSyncJobsQuery, PageResult[SyncJobResponse]]):
    repository: SyncJobRepository
    cabinet_repository: CabinetRepository
    scope_service: OrganizationScopeService

    async def handle(self, query: ListSyncJobsQuery) -> PageResult[SyncJobResponse]:
        await _require_cabinet(
            query.cabinet_id, query.user, "cabinet:view", self.cabinet_repository, self.scope_service
        )
        filters = SyncJobFilter(cabinet_id=query.cabinet_id)
        filters.set_pagination(Pagination(query.page, query.page_size))
        result = await self.repository.find_by_filter(SyncJob, filters)
        return PageResult(
            items=[SyncJobResponse.model_validate(item) for item in result.items],
            total=result.total,
            page=result.page,
            page_size=result.page_size,
        )


@dataclass(frozen=True)
class GetSyncJobQuery(BaseQuery):
    user: UserJWTData
    job_id: UUID


@dataclass(frozen=True)
class GetSyncJobHandler(BaseQueryHandler[GetSyncJobQuery, SyncJobResponse]):
    repository: SyncJobRepository
    cabinet_repository: CabinetRepository
    scope_service: OrganizationScopeService

    async def handle(self, query: GetSyncJobQuery) -> SyncJobResponse:
        job = await self.repository.get(query.job_id)
        if job is None:
            raise CabinetNotFoundError
        await _require_cabinet(job.cabinet_id, query.user, "cabinet:view", self.cabinet_repository, self.scope_service)
        return SyncJobResponse.model_validate(job)


@dataclass(frozen=True)
class GetSyncOverviewQuery(BaseQuery):
    user: UserJWTData


@dataclass(frozen=True)
class GetSyncOverviewHandler(BaseQueryHandler[GetSyncOverviewQuery, SyncOverviewResponse]):
    repository: SyncJobRepository

    async def handle(self, query: GetSyncOverviewQuery) -> SyncOverviewResponse:
        member_orgs = select(OrganizationMember.organization_id).where(
            OrganizationMember.user_id == int(query.user.id),
            OrganizationMember.is_active.is_(True),
        )
        counts_result = await self.repository.session.execute(
            select(SyncJob.status, func.count())
            .where(SyncJob.organization_id.in_(member_orgs))
            .group_by(SyncJob.status)
        )
        counts: dict[str, int] = {}
        for job_status, count in counts_result.all():
            counts[job_status] = count
        last_success = await self.repository.session.scalar(
            select(func.max(SyncJob.finished_at)).where(
                SyncJob.organization_id.in_(member_orgs),
                SyncJob.status == SyncStatus.SUCCEEDED,
            )
        )
        return SyncOverviewResponse(
            queued=counts.get(SyncStatus.QUEUED, 0),
            running=counts.get(SyncStatus.RUNNING, 0),
            retry_wait=counts.get(SyncStatus.RETRY_WAIT, 0),
            paused=counts.get(SyncStatus.PAUSED, 0),
            failed=counts.get(SyncStatus.FAILED, 0),
            last_success_at=last_success,
        )
