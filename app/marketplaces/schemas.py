from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.marketplaces.models import Marketplace, SyncKind, SyncStatus


class CabinetCreateRequest(BaseModel):
    organization_id: UUID
    marketplace: Marketplace
    external_id: str = Field(min_length=1, max_length=128)
    name: str = Field(min_length=1, max_length=160)
    credential: str = Field(min_length=1, max_length=16_384, repr=False)


class CabinetUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=160)
    is_active: bool | None = None


class CabinetResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    organization_id: UUID
    marketplace: Marketplace
    external_id: str
    name: str
    currency: str
    timezone: str
    is_active: bool
    credential_masked_hint: str | None = None
    credential_scopes: list[str] = Field(default_factory=list)
    credential_validated_at: datetime | None = None


class CredentialValidateRequest(BaseModel):
    credential: str | None = Field(default=None, min_length=1, max_length=16_384, repr=False)


class CredentialValidationResponse(BaseModel):
    masked_hint: str
    scopes: list[str]
    validated_at: datetime


class SyncStartRequest(BaseModel):
    kinds: set[SyncKind]
    date_from: date
    date_to: date

    @model_validator(mode="after")
    def validate_period(self) -> SyncStartRequest:
        if self.date_to < self.date_from:
            raise ValueError("date_to must not be earlier than date_from")
        return self


class SyncStartResponse(BaseModel):
    job_ids: list[UUID]


class SyncJobResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    organization_id: UUID
    cabinet_id: UUID
    parent_job_id: UUID | None
    kind: SyncKind
    period_from: date
    period_to: date
    status: SyncStatus
    stage: str
    attempts: int
    progress: Decimal
    error_code: str | None
    error_message: str | None
    repeated_error_count: int
    rows_processed: int
    started_at: datetime | None
    finished_at: datetime | None
    next_retry_at: datetime | None


class SyncOverviewResponse(BaseModel):
    queued: int
    running: int
    retry_wait: int
    paused: int
    failed: int
    last_success_at: datetime | None
