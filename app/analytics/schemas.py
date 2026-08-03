from datetime import date, datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field, model_validator


class AnalyticsFilters(BaseModel):
    organization_id: UUID
    date_from: date
    date_to: date
    cabinet_ids: set[UUID] = Field(default_factory=set)
    compare_date_from: date | None = None
    compare_date_to: date | None = None

    @model_validator(mode="after")
    def periods_are_valid(self) -> AnalyticsFilters:
        if self.date_to < self.date_from:
            raise ValueError("date_to must not be earlier than date_from")
        if (self.compare_date_from is None) != (self.compare_date_to is None):
            raise ValueError("Both compare period boundaries are required")
        return self


class PeriodResponse(BaseModel):
    date_from: date
    date_to: date


class MetricResponse(BaseModel):
    code: str
    value: Decimal | None
    unit: str
    previous_value: Decimal | None
    delta: Decimal | None
    delta_percent: Decimal | None
    status: str


class FreshnessResponse(BaseModel):
    cabinet_id: UUID
    last_success_at: datetime | None
    complete_through: date | None
    missing_kinds: list[str]


class AnalyticsOverviewResponse(BaseModel):
    period: PeriodResponse
    compare_period: PeriodResponse
    metrics: list[MetricResponse]
    data_freshness: list[FreshnessResponse]
    warnings: list[str]


class TimeSeriesMetric(BaseModel):
    code: str
    value: Decimal | None


class TimeSeriesPoint(BaseModel):
    business_date: date
    metrics: list[TimeSeriesMetric]


class TimeSeriesResponse(BaseModel):
    period: PeriodResponse
    points: list[TimeSeriesPoint]
    warnings: list[str]


class ClientErrorRequest(BaseModel):
    organization_id: UUID
    timestamp: datetime
    route: str = Field(max_length=2048)
    release: str = Field(default="unknown", max_length=256)
    browser: str | None = Field(default=None, max_length=1024)
    message: str = Field(max_length=4096)
    stack: str | None = Field(default=None, max_length=32_768)
    component_stack: str | None = Field(default=None, max_length=32_768)
    request_id: str | None = Field(default=None, max_length=128)


class ClientErrorResponse(BaseModel):
    id: UUID
    fingerprint: str
    occurrences: int
    last_seen_at: datetime


class ExportRequest(BaseModel):
    format: Literal["csv", "xlsx"]
    filters: AnalyticsFilters


class ExportJobResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: UUID
    organization_id: UUID
    status: Literal["queued", "running", "succeeded", "failed"]
    format: Literal["csv", "xlsx"]
    storage_key: str | None
    error_code: str | None
    created_at: datetime
    updated_at: datetime
    download_url: str | None = None
