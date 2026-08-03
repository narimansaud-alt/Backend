from dataclasses import dataclass
from decimal import Decimal
from uuid import UUID

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.analytics.models import AnalyticsDaily, FinanceTransactionFact
from app.core.commands import BaseCommand, BaseCommandHandler
from app.core.db.repository import PageResult
from app.core.queries import BaseQuery, BaseQueryHandler
from app.core.services.auth.dto import UserJWTData
from app.finance.models import (
    CashFlowTransaction,
    OperatingExpense,
    Plan,
    PlanValue,
    TaxRatePeriod,
)
from app.finance.schemas import (
    CashFlowResponse,
    ExpenseRequest,
    ExpenseResponse,
    FinanceFilters,
    FinanceTransactionResponse,
    PlanRequest,
    PlanResponse,
    ProfitLossLine,
    ProfitLossResponse,
    TaxRateItem,
    TaxRateResponse,
)
from app.organizations.exceptions import OrganizationForbiddenError, OrganizationNotFoundError
from app.organizations.policies import OrganizationScope
from app.organizations.services import OrganizationScopeService


async def _scope(
    service: OrganizationScopeService,
    user: UserJWTData,
    organization_id: UUID,
    permission: str,
) -> OrganizationScope:
    try:
        return await service.require(int(user.id), organization_id, permission)
    except PermissionError as exc:
        raise OrganizationForbiddenError(permission=permission) from exc


@dataclass(frozen=True)
class ManageExpenseCommand(BaseCommand):
    user: UserJWTData
    action: str
    expense_id: UUID | None
    payload: ExpenseRequest | None
    organization_id: UUID


@dataclass(frozen=True)
class ManageExpenseHandler(BaseCommandHandler[ManageExpenseCommand, ExpenseResponse | None]):
    session: AsyncSession
    scope_service: OrganizationScopeService

    async def handle(self, command: ManageExpenseCommand) -> ExpenseResponse | None:
        await _scope(self.scope_service, command.user, command.organization_id, "finance:manage")
        expense = None
        if command.expense_id is not None:
            expense = await self.session.scalar(
                OperatingExpense.select_not_deleted().where(
                    OperatingExpense.id == command.expense_id,
                    OperatingExpense.organization_id == command.organization_id,
                )
            )
            if expense is None:
                raise OrganizationNotFoundError
        if command.action == "delete":
            assert expense is not None
            expense.soft_delete()
            await self.session.commit()
            return None
        assert command.payload is not None
        if expense is None:
            expense = OperatingExpense(**command.payload.model_dump())
            self.session.add(expense)
        else:
            for field, value in command.payload.model_dump().items():
                setattr(expense, field, value)
        await self.session.commit()
        return ExpenseResponse.model_validate(expense)


@dataclass(frozen=True)
class ListExpensesQuery(BaseQuery):
    user: UserJWTData
    filters: FinanceFilters


@dataclass(frozen=True)
class ListExpensesHandler(BaseQueryHandler[ListExpensesQuery, list[ExpenseResponse]]):
    session: AsyncSession
    scope_service: OrganizationScopeService

    async def handle(self, query: ListExpensesQuery) -> list[ExpenseResponse]:
        scope = await _scope(self.scope_service, query.user, query.filters.organization_id, "analytics:view")
        allowed = scope.restrict_cabinets(set(query.filters.cabinet_ids) or None)
        stmt = OperatingExpense.select_not_deleted().where(
            OperatingExpense.organization_id == query.filters.organization_id,
            OperatingExpense.business_date.between(query.filters.date_from, query.filters.date_to),
        )
        if allowed is not None:
            stmt = stmt.where((OperatingExpense.cabinet_id.is_(None)) | (OperatingExpense.cabinet_id.in_(allowed)))
        rows = (await self.session.scalars(stmt.order_by(OperatingExpense.business_date.desc()))).all()
        return [ExpenseResponse.model_validate(row) for row in rows]


@dataclass(frozen=True)
class SetTaxRatesCommand(BaseCommand):
    user: UserJWTData
    organization_id: UUID
    rates: tuple[TaxRateItem, ...]


@dataclass(frozen=True)
class SetTaxRatesHandler(BaseCommandHandler[SetTaxRatesCommand, list[TaxRateResponse]]):
    session: AsyncSession
    scope_service: OrganizationScopeService

    async def handle(self, command: SetTaxRatesCommand) -> list[TaxRateResponse]:
        await _scope(self.scope_service, command.user, command.organization_id, "finance:manage")
        ordered = sorted(command.rates, key=lambda item: item.valid_from)
        for left, right in zip(ordered, ordered[1:], strict=False):
            if left.valid_to is None or left.valid_to >= right.valid_from:
                raise ValueError("Tax rate periods overlap")
        await self.session.execute(
            delete(TaxRatePeriod).where(TaxRatePeriod.organization_id == command.organization_id)
        )
        rows = [TaxRatePeriod(organization_id=command.organization_id, **item.model_dump()) for item in ordered]
        self.session.add_all(rows)
        await self.session.commit()
        return [TaxRateResponse.model_validate(row, from_attributes=True) for row in rows]


@dataclass(frozen=True)
class GetTaxRatesQuery(BaseQuery):
    user: UserJWTData
    organization_id: UUID


@dataclass(frozen=True)
class GetTaxRatesHandler(BaseQueryHandler[GetTaxRatesQuery, list[TaxRateResponse]]):
    session: AsyncSession
    scope_service: OrganizationScopeService

    async def handle(self, query: GetTaxRatesQuery) -> list[TaxRateResponse]:
        await _scope(self.scope_service, query.user, query.organization_id, "analytics:view")
        rows = (
            await self.session.scalars(
                select(TaxRatePeriod)
                .where(TaxRatePeriod.organization_id == query.organization_id)
                .order_by(TaxRatePeriod.valid_from)
            )
        ).all()
        return [TaxRateResponse.model_validate(row, from_attributes=True) for row in rows]


@dataclass(frozen=True)
class ManagePlanCommand(BaseCommand):
    user: UserJWTData
    action: str
    plan_id: UUID | None
    payload: PlanRequest | None
    organization_id: UUID


@dataclass(frozen=True)
class ManagePlanHandler(BaseCommandHandler[ManagePlanCommand, PlanResponse | None]):
    session: AsyncSession
    scope_service: OrganizationScopeService

    async def handle(self, command: ManagePlanCommand) -> PlanResponse | None:
        await _scope(self.scope_service, command.user, command.organization_id, "plan:manage")
        plan = None
        if command.plan_id:
            plan = await self.session.scalar(
                Plan.select_not_deleted().where(
                    Plan.id == command.plan_id, Plan.organization_id == command.organization_id
                )
            )
            if plan is None:
                raise OrganizationNotFoundError
        if command.action == "delete":
            assert plan is not None
            plan.soft_delete()
            await self.session.commit()
            return None
        assert command.payload is not None
        if command.payload.period_to < command.payload.period_from:
            raise ValueError("Plan period is invalid")
        if plan is None:
            plan = Plan(**command.payload.model_dump(exclude={"values"}))
            self.session.add(plan)
            await self.session.flush()
        else:
            for field, value in command.payload.model_dump(exclude={"values", "organization_id"}).items():
                setattr(plan, field, value)
            await self.session.execute(delete(PlanValue).where(PlanValue.plan_id == plan.id))
        self.session.add_all(PlanValue(plan_id=plan.id, **value.model_dump()) for value in command.payload.values)
        await self.session.commit()
        return PlanResponse.model_validate(plan)


@dataclass(frozen=True)
class ListPlansQuery(BaseQuery):
    user: UserJWTData
    organization_id: UUID


@dataclass(frozen=True)
class ListPlansHandler(BaseQueryHandler[ListPlansQuery, list[PlanResponse]]):
    session: AsyncSession
    scope_service: OrganizationScopeService

    async def handle(self, query: ListPlansQuery) -> list[PlanResponse]:
        await _scope(self.scope_service, query.user, query.organization_id, "analytics:view")
        rows = (
            await self.session.scalars(
                Plan.select_not_deleted()
                .where(Plan.organization_id == query.organization_id)
                .order_by(Plan.period_from.desc())
            )
        ).all()
        return [PlanResponse.model_validate(row) for row in rows]


@dataclass(frozen=True)
class ProfitLossQuery(BaseQuery):
    user: UserJWTData
    filters: FinanceFilters


@dataclass(frozen=True)
class ProfitLossHandler(BaseQueryHandler[ProfitLossQuery, ProfitLossResponse]):
    session: AsyncSession
    scope_service: OrganizationScopeService

    async def handle(self, query: ProfitLossQuery) -> ProfitLossResponse:
        scope = await _scope(self.scope_service, query.user, query.filters.organization_id, "analytics:view")
        allowed = scope.restrict_cabinets(set(query.filters.cabinet_ids) or None)
        stmt = select(AnalyticsDaily).where(
            AnalyticsDaily.organization_id == query.filters.organization_id,
            AnalyticsDaily.business_date.between(query.filters.date_from, query.filters.date_to),
        )
        if allowed is not None:
            stmt = stmt.where(AnalyticsDaily.cabinet_id.in_(allowed))
        rows = (await self.session.scalars(stmt)).all()
        totals: dict[str, Decimal] = {}
        warnings: set[str] = set()
        for row in rows:
            for code, value in row.metrics.items():
                if value is not None:
                    totals[code] = totals.get(code, Decimal("0")) + Decimal(str(value))
            warnings.update(
                f"{key.upper()}_DATA_{value.upper()}" for key, value in row.coverage.items() if value != "complete"
            )
        codes = (
            "net_sales",
            "marketplace_commission",
            "logistics",
            "storage",
            "acquiring",
            "cogs",
            "gross_profit",
            "advertising_cost",
            "operating_expenses",
            "penalties",
            "operating_profit",
            "tax",
            "net_profit",
        )
        return ProfitLossResponse(
            period_from=query.filters.date_from,
            period_to=query.filters.date_to,
            lines=[ProfitLossLine(code=code, value=totals.get(code, Decimal("0"))) for code in codes],
            warnings=sorted(warnings),
        )


@dataclass(frozen=True)
class CashFlowQuery(BaseQuery):
    user: UserJWTData
    filters: FinanceFilters


@dataclass(frozen=True)
class CashFlowHandler(BaseQueryHandler[CashFlowQuery, CashFlowResponse]):
    session: AsyncSession
    scope_service: OrganizationScopeService

    async def handle(self, query: CashFlowQuery) -> CashFlowResponse:
        scope = await _scope(self.scope_service, query.user, query.filters.organization_id, "analytics:view")
        allowed = scope.restrict_cabinets(set(query.filters.cabinet_ids) or None)
        stmt = select(CashFlowTransaction).where(
            CashFlowTransaction.organization_id == query.filters.organization_id,
            CashFlowTransaction.business_date.between(query.filters.date_from, query.filters.date_to),
        )
        if allowed is not None:
            stmt = stmt.where(
                (CashFlowTransaction.cabinet_id.is_(None)) | (CashFlowTransaction.cabinet_id.in_(allowed))
            )
        rows = (await self.session.scalars(stmt)).all()
        inflow = sum((row.amount for row in rows if row.direction == "in"), Decimal("0"))
        outflow = sum((row.amount for row in rows if row.direction == "out"), Decimal("0"))
        return CashFlowResponse(inflow=inflow, outflow=outflow, net_cash_flow=inflow - outflow)


@dataclass(frozen=True)
class FinanceTransactionsQuery(BaseQuery):
    user: UserJWTData
    filters: FinanceFilters
    page: int
    page_size: int


@dataclass(frozen=True)
class FinanceTransactionsHandler(BaseQueryHandler[FinanceTransactionsQuery, PageResult[FinanceTransactionResponse]]):
    session: AsyncSession
    scope_service: OrganizationScopeService

    async def handle(self, query: FinanceTransactionsQuery) -> PageResult[FinanceTransactionResponse]:
        scope = await _scope(self.scope_service, query.user, query.filters.organization_id, "analytics:view")
        allowed = scope.restrict_cabinets(set(query.filters.cabinet_ids) or None)
        stmt = select(FinanceTransactionFact).where(
            FinanceTransactionFact.organization_id == query.filters.organization_id,
            FinanceTransactionFact.business_date.between(query.filters.date_from, query.filters.date_to),
        )
        if allowed is not None:
            stmt = stmt.where(FinanceTransactionFact.cabinet_id.in_(allowed))
        total = await self.session.scalar(select(func.count()).select_from(stmt.subquery())) or 0
        rows = (
            await self.session.scalars(
                stmt.order_by(FinanceTransactionFact.business_date.desc())
                .offset((query.page - 1) * query.page_size)
                .limit(query.page_size)
            )
        ).all()
        return PageResult(
            items=[FinanceTransactionResponse.model_validate(row) for row in rows],
            total=total,
            page=query.page,
            page_size=query.page_size,
        )
