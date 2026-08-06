from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import select

from app.auth.models.user import User
from app.core.db.repository import PageResult
from app.core.filters.pagination import Pagination
from app.core.queries import BaseQuery, BaseQueryHandler
from app.core.services.auth.dto import UserJWTData
from app.organizations.exceptions import OrganizationForbiddenError
from app.organizations.filters import MemberFilter, OrganizationFilter
from app.organizations.models import MemberCabinetAccess, Organization, OrganizationMember
from app.organizations.repositories import MemberRepository, OrganizationRepository
from app.organizations.schemas import MemberResponse, OrganizationResponse
from app.organizations.services import OrganizationScopeService


@dataclass(frozen=True)
class ListOrganizationsQuery(BaseQuery):
    user: UserJWTData
    page: int = 1
    page_size: int = 20


@dataclass(frozen=True)
class ListOrganizationsHandler(BaseQueryHandler[ListOrganizationsQuery, PageResult[OrganizationResponse]]):
    repository: OrganizationRepository

    async def handle(self, query: ListOrganizationsQuery) -> PageResult[OrganizationResponse]:
        filters = OrganizationFilter(user_id=int(query.user.id))
        filters.set_pagination(Pagination(query.page, query.page_size))
        result = await self.repository.find_by_filter(Organization, filters)
        return PageResult(
            items=[OrganizationResponse.model_validate(item) for item in result.items],
            total=result.total,
            page=result.page,
            page_size=result.page_size,
        )


@dataclass(frozen=True)
class ListMembersQuery(BaseQuery):
    user: UserJWTData
    organization_id: UUID
    page: int = 1
    page_size: int = 20


@dataclass(frozen=True)
class ListMembersHandler(BaseQueryHandler[ListMembersQuery, PageResult[MemberResponse]]):
    repository: MemberRepository
    scope_service: OrganizationScopeService

    async def handle(self, query: ListMembersQuery) -> PageResult[MemberResponse]:
        try:
            await self.scope_service.require(int(query.user.id), query.organization_id, "member:view")
        except PermissionError as exc:
            raise OrganizationForbiddenError(permission="member:view") from exc
        filters = MemberFilter(organization_id=query.organization_id)
        filters.set_pagination(Pagination(query.page, query.page_size))
        result = await self.repository.find_by_filter(OrganizationMember, filters)
        user_ids = [member.user_id for member in result.items]
        member_ids = [member.id for member in result.items]
        users = {
            user_id: (username, email)
            for user_id, username, email in (
                await self.repository.session.execute(
                    select(User.id, User.username, User.email).where(User.id.in_(user_ids))
                )
            ).all()
        } if user_ids else {}
        cabinet_ids: dict[UUID, list[UUID]] = {member_id: [] for member_id in member_ids}
        if member_ids:
            rows = (
                await self.repository.session.execute(
                    select(MemberCabinetAccess.member_id, MemberCabinetAccess.cabinet_id).where(
                        MemberCabinetAccess.member_id.in_(member_ids)
                    )
                )
            ).all()
            for member_id, cabinet_id in rows:
                cabinet_ids.setdefault(member_id, []).append(cabinet_id)
        return PageResult(
            items=[
                MemberResponse.model_validate(item).model_copy(
                    update={
                        "username": users.get(item.user_id, (None, None))[0],
                        "email": users.get(item.user_id, (None, None))[1],
                        "cabinet_ids": cabinet_ids.get(item.id, []),
                    }
                )
                for item in result.items
            ],
            total=result.total,
            page=result.page,
            page_size=result.page_size,
        )
