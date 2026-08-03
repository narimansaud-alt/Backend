from datetime import date, datetime
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import JSON, Date, DateTime, ForeignKey, Index, Integer, Numeric, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db.base_model import BaseModel, DateMixin


class CommerceFactMixin:
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    organization_id: Mapped[UUID] = mapped_column(ForeignKey("organizations.id", ondelete="RESTRICT"))
    cabinet_id: Mapped[UUID] = mapped_column(ForeignKey("marketplace_cabinets.id", ondelete="RESTRICT"))
    product_id: Mapped[UUID | None] = mapped_column(ForeignKey("products.id", ondelete="SET NULL"))
    marketplace: Mapped[str] = mapped_column(String(24))
    external_key: Mapped[str] = mapped_column(String(256))
    business_date: Mapped[date] = mapped_column(Date)
    quantity: Mapped[Decimal] = mapped_column(Numeric(18, 4))
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 2))
    source_created_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    source_updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    source_payload: Mapped[dict] = mapped_column(JSON, default=dict)


class OrderFact(CommerceFactMixin, BaseModel, DateMixin):
    __tablename__ = "order_facts"
    __table_args__ = (
        UniqueConstraint("marketplace", "cabinet_id", "external_key"),
        Index("ix_order_facts_scope_date", "organization_id", "cabinet_id", "business_date"),
    )


class SaleFact(CommerceFactMixin, BaseModel, DateMixin):
    __tablename__ = "sale_facts"
    __table_args__ = (
        UniqueConstraint("marketplace", "cabinet_id", "external_key"),
        Index("ix_sale_facts_scope_date", "organization_id", "cabinet_id", "business_date"),
    )


class ReturnFact(CommerceFactMixin, BaseModel, DateMixin):
    __tablename__ = "return_facts"
    __table_args__ = (
        UniqueConstraint("marketplace", "cabinet_id", "external_key"),
        Index("ix_return_facts_scope_date", "organization_id", "cabinet_id", "business_date"),
    )


class FinanceTransactionFact(BaseModel, DateMixin):
    __tablename__ = "finance_transaction_facts"
    __table_args__ = (
        UniqueConstraint("marketplace", "cabinet_id", "external_key"),
        Index("ix_finance_facts_scope_date", "organization_id", "cabinet_id", "business_date"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    organization_id: Mapped[UUID] = mapped_column(ForeignKey("organizations.id", ondelete="RESTRICT"))
    cabinet_id: Mapped[UUID] = mapped_column(ForeignKey("marketplace_cabinets.id", ondelete="RESTRICT"))
    product_id: Mapped[UUID | None] = mapped_column(ForeignKey("products.id", ondelete="SET NULL"))
    marketplace: Mapped[str] = mapped_column(String(24))
    external_key: Mapped[str] = mapped_column(String(256))
    operation_type: Mapped[str] = mapped_column(String(96), index=True)
    business_date: Mapped[date] = mapped_column(Date)
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 2))
    source_updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    source_payload: Mapped[dict] = mapped_column(JSON, default=dict)


class AdvertisingDailyFact(BaseModel, DateMixin):
    __tablename__ = "advertising_daily_facts"
    __table_args__ = (
        UniqueConstraint("marketplace", "cabinet_id", "campaign_external_id", "business_date"),
        Index("ix_ad_facts_scope_date", "organization_id", "cabinet_id", "business_date"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    organization_id: Mapped[UUID] = mapped_column(ForeignKey("organizations.id", ondelete="RESTRICT"))
    cabinet_id: Mapped[UUID] = mapped_column(ForeignKey("marketplace_cabinets.id", ondelete="RESTRICT"))
    marketplace: Mapped[str] = mapped_column(String(24))
    campaign_external_id: Mapped[str] = mapped_column(String(160))
    business_date: Mapped[date] = mapped_column(Date)
    cost: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=0)
    impressions: Mapped[int] = mapped_column(Integer, default=0)
    clicks: Mapped[int] = mapped_column(Integer, default=0)
    add_to_cart: Mapped[int] = mapped_column(Integer, default=0)
    orders: Mapped[int] = mapped_column(Integer, default=0)
    sales: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=0)


class AdvertisingProductDailyFact(BaseModel, DateMixin):
    __tablename__ = "advertising_product_daily_facts"
    __table_args__ = (
        UniqueConstraint("marketplace", "cabinet_id", "campaign_external_id", "product_id", "business_date"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    organization_id: Mapped[UUID] = mapped_column(ForeignKey("organizations.id", ondelete="RESTRICT"))
    cabinet_id: Mapped[UUID] = mapped_column(ForeignKey("marketplace_cabinets.id", ondelete="RESTRICT"))
    product_id: Mapped[UUID] = mapped_column(ForeignKey("products.id", ondelete="RESTRICT"))
    marketplace: Mapped[str] = mapped_column(String(24))
    campaign_external_id: Mapped[str] = mapped_column(String(160))
    business_date: Mapped[date] = mapped_column(Date)
    cost: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=0)
    impressions: Mapped[int] = mapped_column(Integer, default=0)
    clicks: Mapped[int] = mapped_column(Integer, default=0)
    orders: Mapped[int] = mapped_column(Integer, default=0)
    sales: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=0)


class StockDailyFact(BaseModel, DateMixin):
    __tablename__ = "stock_daily_facts"
    __table_args__ = (
        UniqueConstraint("marketplace", "cabinet_id", "external_key", "business_date"),
        Index("ix_stock_facts_scope_date", "organization_id", "cabinet_id", "business_date"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    organization_id: Mapped[UUID] = mapped_column(ForeignKey("organizations.id", ondelete="RESTRICT"))
    cabinet_id: Mapped[UUID] = mapped_column(ForeignKey("marketplace_cabinets.id", ondelete="RESTRICT"))
    product_id: Mapped[UUID | None] = mapped_column(ForeignKey("products.id", ondelete="SET NULL"))
    marketplace: Mapped[str] = mapped_column(String(24))
    external_key: Mapped[str] = mapped_column(String(256))
    business_date: Mapped[date] = mapped_column(Date)
    quantity: Mapped[Decimal] = mapped_column(Numeric(18, 4))


class AnalyticsDaily(BaseModel, DateMixin):
    __tablename__ = "analytics_daily"
    __table_args__ = (
        Index(
            "uq_analytics_daily_grain",
            "cabinet_id",
            "product_id",
            "business_date",
            unique=True,
            postgresql_nulls_not_distinct=True,
        ),
        Index("ix_analytics_daily_scope_date", "organization_id", "cabinet_id", "business_date"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    organization_id: Mapped[UUID] = mapped_column(ForeignKey("organizations.id", ondelete="RESTRICT"))
    cabinet_id: Mapped[UUID] = mapped_column(ForeignKey("marketplace_cabinets.id", ondelete="RESTRICT"))
    product_id: Mapped[UUID | None] = mapped_column(ForeignKey("products.id", ondelete="SET NULL"))
    business_date: Mapped[date] = mapped_column(Date)
    metrics: Mapped[dict] = mapped_column(JSON, default=dict)
    coverage: Mapped[dict] = mapped_column(JSON, default=dict)


class CustomMetric(BaseModel, DateMixin):
    __tablename__ = "custom_metrics"
    __table_args__ = (UniqueConstraint("organization_id", "code"),)

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    organization_id: Mapped[UUID] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"))
    code: Mapped[str] = mapped_column(String(64))
    name: Mapped[str] = mapped_column(String(160))
    expression: Mapped[str] = mapped_column(String(512))
    parsed_ast: Mapped[dict] = mapped_column(JSON)


class ExportJob(BaseModel, DateMixin):
    __tablename__ = "export_jobs"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    organization_id: Mapped[UUID] = mapped_column(ForeignKey("organizations.id", ondelete="RESTRICT"))
    requested_by_user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))
    status: Mapped[str] = mapped_column(String(24), default="queued", index=True)
    format: Mapped[str] = mapped_column(String(8))
    filters: Mapped[dict] = mapped_column(JSON)
    storage_key: Mapped[str | None] = mapped_column(String(512))
    error_code: Mapped[str | None] = mapped_column(String(64))


class ClientErrorEvent(BaseModel):
    __tablename__ = "client_error_events"
    __table_args__ = (
        UniqueConstraint("organization_id", "fingerprint", "release"),
        Index("ix_client_errors_last_seen", "organization_id", "last_seen_at"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    organization_id: Mapped[UUID] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"))
    fingerprint: Mapped[str] = mapped_column(String(64))
    route: Mapped[str] = mapped_column(String(512))
    release: Mapped[str] = mapped_column(String(128), default="unknown")
    browser: Mapped[str | None] = mapped_column(String(256))
    message: Mapped[str] = mapped_column(String(1024))
    stack: Mapped[str | None] = mapped_column(Text)
    component_stack: Mapped[str | None] = mapped_column(Text)
    request_id: Mapped[str | None] = mapped_column(String(64))
    occurrences: Mapped[int] = mapped_column(Integer, default=1)
    first_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
