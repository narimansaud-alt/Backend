from datetime import date
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import Date, ForeignKey, Index, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db.base_model import BaseModel, DateMixin, SoftDeleteMixin


class ProductGroup(BaseModel, DateMixin, SoftDeleteMixin):
    __tablename__ = "product_groups"
    __table_args__ = (UniqueConstraint("organization_id", "name"),)

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    organization_id: Mapped[UUID] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(160))


class Product(BaseModel, DateMixin, SoftDeleteMixin):
    __tablename__ = "products"
    __table_args__ = (UniqueConstraint("organization_id", "internal_sku"),)

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    organization_id: Mapped[UUID] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"), index=True)
    group_id: Mapped[UUID | None] = mapped_column(ForeignKey("product_groups.id", ondelete="SET NULL"))
    internal_sku: Mapped[str] = mapped_column(String(128))
    name: Mapped[str] = mapped_column(String(512))
    brand: Mapped[str | None] = mapped_column(String(160))
    category: Mapped[str | None] = mapped_column(String(256))


class MarketplaceOffer(BaseModel, DateMixin):
    __tablename__ = "marketplace_offers"
    __table_args__ = (
        UniqueConstraint("cabinet_id", "external_offer_id"),
        Index("ix_marketplace_offers_product_cabinet", "product_id", "cabinet_id"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    product_id: Mapped[UUID] = mapped_column(ForeignKey("products.id", ondelete="RESTRICT"))
    cabinet_id: Mapped[UUID] = mapped_column(ForeignKey("marketplace_cabinets.id", ondelete="RESTRICT"), index=True)
    marketplace: Mapped[str] = mapped_column(String(24))
    external_offer_id: Mapped[str] = mapped_column(String(160))
    external_product_id: Mapped[str | None] = mapped_column(String(160))
    barcode: Mapped[str | None] = mapped_column(String(64))


class ProductCostHistory(BaseModel, DateMixin):
    __tablename__ = "product_cost_history"
    __table_args__ = (
        UniqueConstraint("product_id", "valid_from"),
        Index("ix_product_cost_effective", "product_id", "valid_from", "valid_to"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    product_id: Mapped[UUID] = mapped_column(ForeignKey("products.id", ondelete="RESTRICT"))
    valid_from: Mapped[date] = mapped_column(Date)
    valid_to: Mapped[date | None] = mapped_column(Date)
    unit_cost: Mapped[Decimal] = mapped_column(Numeric(18, 4))
    currency: Mapped[str] = mapped_column(String(3), default="RUB")
