from dataclasses import dataclass
from typing import cast
from uuid import UUID

from sqlalchemy import Select, select

from app.core.db.repository import IRepository
from app.organizations.filters import MemberFilter, OrganizationFilter
from app.organizations.models import Organization, OrganizationMember


@dataclass
class OrganizationRepository(IRepository[Organization, OrganizationFilter]):
    async def get(self, organization_id: UUID) -> Organization | None:
        return cast(
            Organization | None,
            await self.session.scalar(
                select(Organization).where(
                    Organization.id == organization_id,
                    Organization.is_active.is_(True),
                )
            ),
        )

    def apply_relationship_filters(self, stmt: Select, filters: OrganizationFilter) -> Select:
        if filters.user_id is not None:
            stmt = stmt.join(
                OrganizationMember,
                OrganizationMember.organization_id == Organization.id,
            ).where(
                OrganizationMember.user_id == filters.user_id,
                OrganizationMember.is_active.is_(True),
            )
        return stmt


@dataclass
class MemberRepository(IRepository[OrganizationMember, MemberFilter]):
    async def get(self, member_id: UUID, organization_id: UUID) -> OrganizationMember | None:
        return cast(
            OrganizationMember | None,
            await self.session.scalar(
                select(OrganizationMember).where(
                    OrganizationMember.id == member_id,
                    OrganizationMember.organization_id == organization_id,
                    OrganizationMember.is_active.is_(True),
                )
            ),
        )

    def apply_relationship_filters(self, stmt: Select, filters: MemberFilter) -> Select:
        return stmt
