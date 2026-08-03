from datetime import date
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import JSON, Date, ForeignKey, Index, Numeric, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db.base_model import BaseModel, DateMixin, SoftDeleteMixin


class ExpenseCategory(BaseModel, DateMixin, SoftDeleteMixin):
    __tablename__ = "expense_categories"
    __table_args__ = (UniqueConstraint("organization_id", "name"),)

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    organization_id: Mapped[UUID] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"))
    name: Mapped[str] = mapped_column(String(160))
    cash_flow_code: Mapped[str | None] = mapped_column(String(64))


class OperatingExpense(BaseModel, DateMixin, SoftDeleteMixin):
    __tablename__ = "operating_expenses"
    __table_args__ = (Index("ix_expenses_scope_date", "organization_id", "cabinet_id", "business_date"),)

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    organization_id: Mapped[UUID] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"))
    cabinet_id: Mapped[UUID | None] = mapped_column(ForeignKey("marketplace_cabinets.id", ondelete="RESTRICT"))
    category_id: Mapped[UUID] = mapped_column(ForeignKey("expense_categories.id", ondelete="RESTRICT"))
    business_date: Mapped[date] = mapped_column(Date)
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 2))
    description: Mapped[str | None] = mapped_column(Text)


class TaxRatePeriod(BaseModel, DateMixin):
    __tablename__ = "tax_rate_periods"
    __table_args__ = (UniqueConstraint("organization_id", "valid_from"),)

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    organization_id: Mapped[UUID] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"))
    valid_from: Mapped[date] = mapped_column(Date)
    valid_to: Mapped[date | None] = mapped_column(Date)
    rate_percent: Mapped[Decimal] = mapped_column(Numeric(7, 4))
    base_metric: Mapped[str] = mapped_column(String(64), default="net_sales")


class CashFlowTransaction(BaseModel, DateMixin):
    __tablename__ = "cash_flow_transactions"
    __table_args__ = (Index("ix_cash_flow_scope_date", "organization_id", "business_date"),)

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    organization_id: Mapped[UUID] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"))
    cabinet_id: Mapped[UUID | None] = mapped_column(ForeignKey("marketplace_cabinets.id", ondelete="RESTRICT"))
    category_id: Mapped[UUID | None] = mapped_column(ForeignKey("expense_categories.id", ondelete="SET NULL"))
    business_date: Mapped[date] = mapped_column(Date)
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 2))
    direction: Mapped[str] = mapped_column(String(8))
    counterparty: Mapped[str | None] = mapped_column(String(256))
    description: Mapped[str | None] = mapped_column(Text)


class Plan(BaseModel, DateMixin, SoftDeleteMixin):
    __tablename__ = "plans"
    __table_args__ = (UniqueConstraint("organization_id", "name", "period_from", "period_to"),)

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    organization_id: Mapped[UUID] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"))
    name: Mapped[str] = mapped_column(String(160))
    period_from: Mapped[date] = mapped_column(Date)
    period_to: Mapped[date] = mapped_column(Date)


class PlanValue(BaseModel, DateMixin):
    __tablename__ = "plan_values"
    __table_args__ = (UniqueConstraint("plan_id", "cabinet_id", "product_id", "metric_code"),)

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    plan_id: Mapped[UUID] = mapped_column(ForeignKey("plans.id", ondelete="CASCADE"))
    cabinet_id: Mapped[UUID | None] = mapped_column(ForeignKey("marketplace_cabinets.id", ondelete="RESTRICT"))
    product_id: Mapped[UUID | None] = mapped_column(ForeignKey("products.id", ondelete="RESTRICT"))
    metric_code: Mapped[str] = mapped_column(String(64))
    value: Mapped[Decimal] = mapped_column(Numeric(18, 4))
    dimensions: Mapped[dict] = mapped_column(JSON, default=dict)
