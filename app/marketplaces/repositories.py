from dataclasses import dataclass
from typing import cast
from uuid import UUID

from sqlalchemy import Select, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db.repository import IRepository
from app.marketplaces.filters import CabinetFilter, SyncJobFilter
from app.marketplaces.models import MarketplaceCabinet, MarketplaceCredential, SyncJob


@dataclass
class CabinetRepository(IRepository[MarketplaceCabinet, CabinetFilter]):
    async def get(self, cabinet_id: UUID) -> MarketplaceCabinet | None:
        return cast(
            MarketplaceCabinet | None,
            await self.session.scalar(
                MarketplaceCabinet.select_not_deleted().where(MarketplaceCabinet.id == cabinet_id)
            ),
        )

    def apply_relationship_filters(self, stmt: Select, filters: CabinetFilter) -> Select:
        return stmt


@dataclass
class SyncJobRepository(IRepository[SyncJob, SyncJobFilter]):
    async def get(self, job_id: UUID) -> SyncJob | None:
        return cast(SyncJob | None, await self.session.scalar(select(SyncJob).where(SyncJob.id == job_id)))

    def apply_relationship_filters(self, stmt: Select, filters: SyncJobFilter) -> Select:
        return stmt


async def get_credential(session: AsyncSession, cabinet_id: UUID) -> MarketplaceCredential | None:
    return cast(
        MarketplaceCredential | None,
        await session.scalar(select(MarketplaceCredential).where(MarketplaceCredential.cabinet_id == cabinet_id)),
    )
