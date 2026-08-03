from datetime import date
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator


class FinanceFilters(BaseModel):
    organization_id: UUID
    date_from: date
    date_to: date
    cabinet_ids: set[UUID] = Field(default_factory=set)

    @model_validator(mode="after")
    def validate_period(self) -> FinanceFilters:
        if self.date_to < self.date_from:
            raise ValueError("date_to must not be earlier than date_from")
        return self


class ExpenseRequest(BaseModel):
    organization_id: UUID
    cabinet_id: UUID | None = None
    category_id: UUID
    business_date: date
    amount: Decimal = Field(ge=0)
    description: str | None = Field(default=None, max_length=2048)


class ExpenseResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    organization_id: UUID
    cabinet_id: UUID | None
    category_id: UUID
    business_date: date
    amount: Decimal
    description: str | None


class TaxRateItem(BaseModel):
    valid_from: date
    valid_to: date | None = None
    rate_percent: Decimal = Field(ge=0, le=100)
    base_metric: str = Field(default="net_sales", max_length=64)


class TaxRatesRequest(BaseModel):
    organization_id: UUID
    rates: list[TaxRateItem]


class TaxRateResponse(TaxRateItem):
    id: UUID


class PlanValueRequest(BaseModel):
    cabinet_id: UUID | None = None
    product_id: UUID | None = None
    metric_code: str = Field(max_length=64)
    value: Decimal


class PlanRequest(BaseModel):
    organization_id: UUID
    name: str = Field(min_length=1, max_length=160)
    period_from: date
    period_to: date
    values: list[PlanValueRequest] = Field(default_factory=list)


class PlanResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    organization_id: UUID
    name: str
    period_from: date
    period_to: date


class ProfitLossLine(BaseModel):
    code: str
    value: Decimal


class ProfitLossResponse(BaseModel):
    period_from: date
    period_to: date
    lines: list[ProfitLossLine]
    warnings: list[str]


class CashFlowResponse(BaseModel):
    inflow: Decimal
    outflow: Decimal
    net_cash_flow: Decimal


class FinanceTransactionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    cabinet_id: UUID
    marketplace: str
    external_key: str
    operation_type: str
    business_date: date
    amount: Decimal
