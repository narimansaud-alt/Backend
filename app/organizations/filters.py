from dataclasses import dataclass
from uuid import UUID

from app.core.filters.base import BaseFilter
from app.core.filters.condition import FilterOperator


@dataclass
class OrganizationFilter(BaseFilter):
    user_id: int | None = None
    is_active: bool | None = True

    def build_condition(self) -> None:
        self.add_condition("is_active", FilterOperator.EQ, self.is_active)


@dataclass
class MemberFilter(BaseFilter):
    organization_id: UUID | None = None
    role: str | None = None
    is_active: bool | None = True

    def build_condition(self) -> None:
        self.add_condition("organization_id", FilterOperator.EQ, self.organization_id)
        self.add_condition("role", FilterOperator.EQ, self.role)
        self.add_condition("is_active", FilterOperator.EQ, self.is_active)
