from dataclasses import dataclass
from typing import Any

from app.core.exceptions import ApplicationError


@dataclass(kw_only=True)
class OrganizationNotFoundError(ApplicationError):
    code: str = "ORGANIZATION_NOT_FOUND"
    status: int = 404

    @property
    def message(self) -> str:
        return "Organization was not found"

    @property
    def detail(self) -> dict[str, Any]:
        return {}


@dataclass(kw_only=True)
class OrganizationForbiddenError(ApplicationError):
    permission: str
    code: str = "ORGANIZATION_ACCESS_DENIED"
    status: int = 404

    @property
    def message(self) -> str:
        return "Organization resource was not found"

    @property
    def detail(self) -> dict[str, Any]:
        return {"permission": self.permission}


@dataclass(kw_only=True)
class OwnerMutationError(ApplicationError):
    code: str = "OWNER_MUTATION_FORBIDDEN"
    status: int = 409

    @property
    def message(self) -> str:
        return "The organization owner cannot be changed through the member endpoint"
