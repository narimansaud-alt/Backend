from dataclasses import dataclass
from uuid import UUID

from app.organizations.models import OrganizationRole

ROLE_PERMISSIONS: dict[OrganizationRole, frozenset[str]] = {
    OrganizationRole.OWNER: frozenset(
        {
            "organization:view",
            "organization:manage",
            "member:view",
            "member:invite",
            "member:manage",
            "cabinet:view",
            "cabinet:manage",
            "cabinet:sync",
            "analytics:view",
            "analytics:export",
            "cost:manage",
            "finance:manage",
            "plan:manage",
        }
    ),
    OrganizationRole.ADMIN: frozenset(
        {
            "organization:view",
            "organization:manage",
            "member:view",
            "member:invite",
            "member:manage",
            "cabinet:view",
            "cabinet:manage",
            "cabinet:sync",
            "analytics:view",
            "analytics:export",
            "cost:manage",
            "finance:manage",
            "plan:manage",
        }
    ),
    OrganizationRole.MANAGER: frozenset(
        {
            "organization:view",
            "member:view",
            "cabinet:view",
            "cabinet:sync",
            "analytics:view",
            "analytics:export",
            "cost:manage",
            "plan:manage",
        }
    ),
    OrganizationRole.VIEWER: frozenset(
        {
            "organization:view",
            "cabinet:view",
            "analytics:view",
        }
    ),
}


@dataclass(frozen=True)
class OrganizationScope:
    organization_id: UUID
    role: OrganizationRole
    permissions: frozenset[str]
    cabinet_ids: frozenset[UUID] | None

    def permits(self, permission: str) -> bool:
        return permission in self.permissions

    def restrict_cabinets(self, requested: set[UUID] | None) -> frozenset[UUID] | None:
        if self.cabinet_ids is None:
            return None if requested is None else frozenset(requested)
        if requested is None:
            return self.cabinet_ids
        return frozenset(requested) & self.cabinet_ids


def permissions_for_role(role: OrganizationRole) -> frozenset[str]:
    return ROLE_PERMISSIONS[role]
