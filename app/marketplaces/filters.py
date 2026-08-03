from dataclasses import dataclass
from datetime import date
from uuid import UUID

from app.core.filters.base import BaseFilter
from app.core.filters.condition import FilterOperator


@dataclass
class CabinetFilter(BaseFilter):
    organization_ids: list[UUID] | None = None
    cabinet_ids: list[UUID] | None = None
    marketplace: str | None = None
    is_active: bool | None = True

    def build_condition(self) -> None:
        self.add_condition("organization_id", FilterOperator.IN, self.organization_ids)
        self.add_condition("id", FilterOperator.IN, self.cabinet_ids)
        self.add_condition("marketplace", FilterOperator.EQ, self.marketplace)
        self.add_condition("is_active", FilterOperator.EQ, self.is_active)


@dataclass
class SyncJobFilter(BaseFilter):
    organization_id: UUID | None = None
    cabinet_id: UUID | None = None
    status: str | None = None
    kind: str | None = None
    period_from: date | None = None
    period_to: date | None = None

    def build_condition(self) -> None:
        self.add_condition("organization_id", FilterOperator.EQ, self.organization_id)
        self.add_condition("cabinet_id", FilterOperator.EQ, self.cabinet_id)
        self.add_condition("status", FilterOperator.EQ, self.status)
        self.add_condition("kind", FilterOperator.EQ, self.kind)
        self.add_condition("period_from", FilterOperator.GTE, self.period_from)
        self.add_condition("period_to", FilterOperator.LTE, self.period_to)
