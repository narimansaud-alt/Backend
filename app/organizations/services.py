from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.marketplaces.models import MarketplaceCabinet
from app.organizations.models import MemberCabinetAccess, OrganizationMember, OrganizationRole
from app.organizations.policies import OrganizationScope, permissions_for_role


class OrganizationAccessDeniedError(PermissionError):
    pass


@dataclass
class OrganizationScopeService:
    session: AsyncSession

    async def get_scope(self, user_id: int, organization_id: UUID) -> OrganizationScope | None:
        member_result = await self.session.execute(
            select(OrganizationMember).where(
                OrganizationMember.organization_id == organization_id,
                OrganizationMember.user_id == user_id,
                OrganizationMember.is_active.is_(True),
            )
        )
        member = member_result.scalar_one_or_none()
        if member is None:
            return None

        role = OrganizationRole(member.role)
        cabinet_ids: frozenset[UUID] | None = None
        if role in {OrganizationRole.MANAGER, OrganizationRole.VIEWER}:
            rows = await self.session.scalars(
                select(MemberCabinetAccess.cabinet_id)
                .join(MarketplaceCabinet, MarketplaceCabinet.id == MemberCabinetAccess.cabinet_id)
                .where(
                    MemberCabinetAccess.member_id == member.id,
                    MarketplaceCabinet.organization_id == organization_id,
                    MarketplaceCabinet.deleted_at.is_(None),
                )
            )
            cabinet_ids = frozenset(rows.all())

        return OrganizationScope(
            organization_id=organization_id,
            role=role,
            permissions=permissions_for_role(role),
            cabinet_ids=cabinet_ids,
        )

    async def require(self, user_id: int, organization_id: UUID, permission: str) -> OrganizationScope:
        scope = await self.get_scope(user_id, organization_id)
        if scope is None or not scope.permits(permission):
            raise OrganizationAccessDeniedError("Organization resource was not found or is not accessible")
        return scope
