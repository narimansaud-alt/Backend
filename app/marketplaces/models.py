from datetime import date, datetime
from decimal import Decimal
from enum import StrEnum
from uuid import UUID, uuid4

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    LargeBinary,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db.base_model import BaseModel, DateMixin, SoftDeleteMixin


class Marketplace(StrEnum):
    WILDBERRIES = "wildberries"
    OZON = "ozon"
    YANDEX_MARKET = "yandex_market"


class SyncKind(StrEnum):
    CATALOG = "catalog"
    ORDERS = "orders"
    SALES_RETURNS = "sales_returns"
    FINANCE_TRANSACTIONS = "finance_transactions"
    ADVERTISING = "advertising"
    STOCKS = "stocks"
    ANALYTICS_FUNNEL = "analytics_funnel"
    RECOMPUTE_DAILY_ANALYTICS = "recompute_daily_analytics"


class SyncStatus(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    RETRY_WAIT = "retry_wait"
    PAUSED = "paused"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"


ACTIVE_SYNC_STATUSES = (
    SyncStatus.QUEUED.value,
    SyncStatus.RUNNING.value,
    SyncStatus.RETRY_WAIT.value,
)


class MarketplaceCabinet(BaseModel, DateMixin, SoftDeleteMixin):
    __tablename__ = "marketplace_cabinets"
    __table_args__ = (UniqueConstraint("organization_id", "marketplace", "external_id"),)

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    organization_id: Mapped[UUID] = mapped_column(ForeignKey("organizations.id", ondelete="RESTRICT"), index=True)
    marketplace: Mapped[str] = mapped_column(String(24), index=True)
    external_id: Mapped[str] = mapped_column(String(128))
    name: Mapped[str] = mapped_column(String(160))
    currency: Mapped[str] = mapped_column(String(3), default="RUB")
    timezone: Mapped[str] = mapped_column(String(64), default="Europe/Moscow")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)


class MarketplaceCredential(BaseModel, DateMixin):
    __tablename__ = "marketplace_credentials"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    cabinet_id: Mapped[UUID] = mapped_column(ForeignKey("marketplace_cabinets.id", ondelete="CASCADE"), unique=True)
    encrypted_value: Mapped[bytes] = mapped_column(LargeBinary)
    key_version: Mapped[int] = mapped_column(Integer)
    scopes: Mapped[list[str]] = mapped_column(JSON, default=list)
    masked_hint: Mapped[str] = mapped_column(String(32))
    validated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    validation_error_code: Mapped[str | None] = mapped_column(String(64))
    revision: Mapped[int] = mapped_column(Integer, default=1)


class SyncJob(BaseModel, DateMixin):
    __tablename__ = "sync_jobs"
    __table_args__ = (
        CheckConstraint("progress >= 0 AND progress <= 100", name="ck_sync_jobs_progress"),
        UniqueConstraint("idempotency_key"),
        Index(
            "uq_sync_jobs_active_window",
            "cabinet_id",
            "kind",
            "period_from",
            "period_to",
            unique=True,
            postgresql_where=text("status IN ('queued', 'running', 'retry_wait')"),
        ),
        Index("ix_sync_jobs_status_created", "status", "created_at"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    organization_id: Mapped[UUID] = mapped_column(ForeignKey("organizations.id", ondelete="RESTRICT"), index=True)
    cabinet_id: Mapped[UUID] = mapped_column(ForeignKey("marketplace_cabinets.id", ondelete="RESTRICT"), index=True)
    parent_job_id: Mapped[UUID | None] = mapped_column(ForeignKey("sync_jobs.id", ondelete="SET NULL"))
    kind: Mapped[str] = mapped_column(String(48), index=True)
    period_from: Mapped[date] = mapped_column(Date)
    period_to: Mapped[date] = mapped_column(Date)
    status: Mapped[str] = mapped_column(String(24), default=SyncStatus.QUEUED, index=True)
    stage: Mapped[str] = mapped_column(String(64), default="queued")
    idempotency_key: Mapped[str] = mapped_column(String(128))
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    progress: Mapped[Decimal] = mapped_column(Numeric(5, 2), default=0)
    cursor: Mapped[dict | None] = mapped_column(JSON)
    error_code: Mapped[str | None] = mapped_column(String(64))
    error_message: Mapped[str | None] = mapped_column(String(512))
    repeated_error_count: Mapped[int] = mapped_column(Integer, default=0)
    rows_processed: Mapped[int] = mapped_column(Integer, default=0)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    next_retry_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)


class SyncCheckpoint(BaseModel, DateMixin):
    __tablename__ = "sync_checkpoints"
    __table_args__ = (UniqueConstraint("job_id", "endpoint_group"),)

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    job_id: Mapped[UUID] = mapped_column(ForeignKey("sync_jobs.id", ondelete="CASCADE"), index=True)
    endpoint_group: Mapped[str] = mapped_column(String(64))
    cursor: Mapped[dict] = mapped_column(JSON, default=dict)
    page_number: Mapped[int] = mapped_column(Integer, default=0)
    rows_processed: Mapped[int] = mapped_column(Integer, default=0)
    complete_through: Mapped[date | None] = mapped_column(Date)


class SyncJobEvent(BaseModel):
    __tablename__ = "sync_job_events"
    __table_args__ = (Index("ix_sync_job_events_job_created", "job_id", "created_at"),)

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    job_id: Mapped[UUID] = mapped_column(ForeignKey("sync_jobs.id", ondelete="CASCADE"))
    level: Mapped[str] = mapped_column(String(16))
    code: Mapped[str] = mapped_column(String(64))
    safe_message: Mapped[str] = mapped_column(Text)
    details: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=text("now()"))
