from dataclasses import dataclass
from typing import Any

from app.core.exceptions import ApplicationError


@dataclass(kw_only=True)
class CabinetNotFoundError(ApplicationError):
    code: str = "CABINET_NOT_FOUND"
    status: int = 404

    @property
    def message(self) -> str:
        return "Cabinet was not found"


@dataclass(kw_only=True)
class MarketplaceRequestError(ApplicationError):
    error_code: str
    safe_message: str
    code: str = "MARKETPLACE_ERROR"
    status: int = 422

    @property
    def message(self) -> str:
        return self.safe_message

    @property
    def detail(self) -> dict[str, Any]:
        return {"marketplace_code": self.error_code}


@dataclass(kw_only=True)
class SyncConflictError(ApplicationError):
    code: str = "SYNC_CONFLICT"
    status: int = 409

    @property
    def message(self) -> str:
        return "An active synchronization already exists"


@dataclass(kw_only=True)
class UnsupportedSyncKindError(ApplicationError):
    marketplace: str
    kind: str
    code: str = "SYNC_KIND_UNSUPPORTED"
    status: int = 422

    @property
    def message(self) -> str:
        return "The marketplace connector does not support this synchronization kind"

    @property
    def detail(self) -> dict[str, Any]:
        return {"marketplace": self.marketplace, "kind": self.kind}
