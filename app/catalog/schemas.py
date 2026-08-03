from datetime import date
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ProductResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    organization_id: UUID
    group_id: UUID | None
    internal_sku: str
    name: str
    brand: str | None
    category: str | None


class ProductUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=512)
    group_id: UUID | None = None


class ProductCostImportRow(BaseModel):
    product_id: UUID
    valid_from: date
    valid_to: date | None = None
    unit_cost: Decimal = Field(ge=0)
    currency: str = Field(default="RUB", min_length=3, max_length=3)


class ProductCostImportRequest(BaseModel):
    organization_id: UUID
    rows: list[ProductCostImportRow] = Field(min_length=1, max_length=10_000)


class ProductGroupCreateRequest(BaseModel):
    organization_id: UUID
    name: str = Field(min_length=1, max_length=160)


class ProductGroupUpdateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=160)


class ProductGroupResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    organization_id: UUID
    name: str
