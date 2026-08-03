from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.analytics.formulas import MetricInputs, calculate_metrics
from app.analytics.models import AnalyticsDaily, OrderFact, ReturnFact, SaleFact
from app.catalog.models import ProductCostHistory
from app.marketplaces.models import SyncJob


def _decimal(value: Decimal | None) -> Decimal:
    return value or Decimal("0")


@dataclass
class AnalyticsProjectionService:
    session: AsyncSession

    async def recompute(self, job: SyncJob) -> None:
        grain: dict[tuple[date, UUID | None], MetricInputs] = {}
        sources = (
            (OrderFact, "orders_amount", "orders_qty"),
            (SaleFact, "sales_amount", "sales_qty"),
            (ReturnFact, "returns_amount", "returns_qty"),
        )
        for model, amount_name, quantity_name in sources:
            rows = (
                await self.session.execute(
                    select(
                        model.business_date,
                        model.product_id,
                        func.sum(model.amount),
                        func.sum(model.quantity),
                    )
                    .where(
                        model.cabinet_id == job.cabinet_id,
                        model.business_date.between(job.period_from, job.period_to),
                    )
                    .group_by(model.business_date, model.product_id)
                )
            ).all()
            for business_date, product_id, amount, quantity in rows:
                current = grain.get((business_date, product_id), MetricInputs())
                values = {field: getattr(current, field) for field in current.__dataclass_fields__}
                values[amount_name] = _decimal(amount)
                values[quantity_name] = _decimal(quantity)
                grain[(business_date, product_id)] = MetricInputs(**values)

        for (business_date, product_id), current in grain.items():
            unit_cost = Decimal("0")
            has_cost = product_id is None
            if product_id is not None:
                cost = await self.session.scalar(
                    select(ProductCostHistory.unit_cost)
                    .where(
                        ProductCostHistory.product_id == product_id,
                        ProductCostHistory.valid_from <= business_date,
                        (ProductCostHistory.valid_to.is_(None)) | (ProductCostHistory.valid_to >= business_date),
                    )
                    .order_by(ProductCostHistory.valid_from.desc())
                    .limit(1)
                )
                if cost is not None:
                    unit_cost = cost
                    has_cost = True
            values = {field: getattr(current, field) for field in current.__dataclass_fields__}
            values["cogs"] = current.sales_qty * unit_cost
            metrics = calculate_metrics(MetricInputs(**values))
            serialized = {key: str(value) if value is not None else None for key, value in metrics.items()}
            coverage = {
                "cost": "complete" if has_cost else "missing",
                "advertising": "missing",
                "finance": "missing",
            }
            stmt = (
                insert(AnalyticsDaily)
                .values(
                    organization_id=job.organization_id,
                    cabinet_id=job.cabinet_id,
                    product_id=product_id,
                    business_date=business_date,
                    metrics=serialized,
                    coverage=coverage,
                )
                .on_conflict_do_update(
                    index_elements=[
                        AnalyticsDaily.cabinet_id,
                        AnalyticsDaily.product_id,
                        AnalyticsDaily.business_date,
                    ],
                    set_={"metrics": serialized, "coverage": coverage},
                )
            )
            await self.session.execute(stmt)
        await self.session.commit()
