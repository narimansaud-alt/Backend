from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.analytics.models import ClientErrorEvent
from app.analytics.schemas import ClientErrorResponse
from app.core.db.repository import PageResult
from app.core.queries import BaseQuery, BaseQueryHandler
from app.core.services.auth.dto import UserJWTData
from app.organizations.exceptions import OrganizationForbiddenError
from app.organizations.models import OrganizationRole
from app.organizations.services import OrganizationScopeService


@dataclass(frozen=True)
class ListClientErrorsQuery(BaseQuery):
    user: UserJWTData
    organization_id: UUID
    page: int
    page_size: int


@dataclass(frozen=True)
class ListClientErrorsHandler(BaseQueryHandler[ListClientErrorsQuery, PageResult[ClientErrorResponse]]):
    session: AsyncSession
    scope_service: OrganizationScopeService

    async def handle(self, query: ListClientErrorsQuery) -> PageResult[ClientErrorResponse]:
        scope = await self.scope_service.get_scope(int(query.user.id), query.organization_id)
        if scope is None or scope.role not in {OrganizationRole.OWNER, OrganizationRole.ADMIN}:
            raise OrganizationForbiddenError(permission="organization:manage")
        base = select(ClientErrorEvent).where(ClientErrorEvent.organization_id == query.organization_id)
        total = await self.session.scalar(select(func.count()).select_from(base.subquery())) or 0
        rows = (
            await self.session.scalars(
                base.order_by(ClientErrorEvent.last_seen_at.desc())
                .offset((query.page - 1) * query.page_size)
                .limit(query.page_size)
            )
        ).all()
        return PageResult(
            items=[
                ClientErrorResponse(
                    id=row.id,
                    fingerprint=row.fingerprint,
                    occurrences=row.occurrences,
                    last_seen_at=row.last_seen_at,
                )
                for row in rows
            ],
            total=total,
            page=query.page,
            page_size=query.page_size,
        )
