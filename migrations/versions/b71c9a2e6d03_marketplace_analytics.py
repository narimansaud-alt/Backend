"""Marketplace analytics domain schema.

Revision ID: b71c9a2e6d03
Revises: a2db5de794b4
Create Date: 2026-08-03
"""

from collections.abc import Sequence

from alembic import op

from app.core.models import BaseModel

revision: str = "b71c9a2e6d03"
down_revision: str | None = "a2db5de794b4"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


DOMAIN_TABLES = frozenset(
    {
        "organizations",
        "organization_members",
        "member_cabinet_access",
        "organization_invitations",
        "marketplace_cabinets",
        "marketplace_credentials",
        "sync_jobs",
        "sync_checkpoints",
        "sync_job_events",
        "products",
        "marketplace_offers",
        "product_groups",
        "product_cost_history",
        "order_facts",
        "sale_facts",
        "return_facts",
        "finance_transaction_facts",
        "advertising_daily_facts",
        "advertising_product_daily_facts",
        "stock_daily_facts",
        "analytics_daily",
        "expense_categories",
        "operating_expenses",
        "tax_rate_periods",
        "cash_flow_transactions",
        "plans",
        "plan_values",
        "custom_metrics",
        "export_jobs",
        "client_error_events",
    }
)


def upgrade() -> None:
    bind = op.get_bind()
    for table in BaseModel.metadata.sorted_tables:
        if table.name in DOMAIN_TABLES:
            table.create(bind, checkfirst=False)


def downgrade() -> None:
    bind = op.get_bind()
    for table in reversed(BaseModel.metadata.sorted_tables):
        if table.name in DOMAIN_TABLES:
            table.drop(bind, checkfirst=False)
