from typing import Annotated
from uuid import UUID

from dishka import FromDishka
from dishka.integrations.fastapi import DishkaRoute
from fastapi import APIRouter, Query, Response, status

from app.auth.deps import AuthCurrentUserJWTData
from app.core.db.repository import PageResult
from app.core.mediators.base import BaseMediator
from app.finance.application import (
    CashFlowQuery,
    FinanceTransactionsQuery,
    GetTaxRatesQuery,
    ListExpensesQuery,
    ListPlansQuery,
    ManageExpenseCommand,
    ManagePlanCommand,
    ProfitLossQuery,
    SetTaxRatesCommand,
)
from app.finance.schemas import (
    CashFlowResponse,
    ExpenseRequest,
    ExpenseResponse,
    FinanceFilters,
    FinanceTransactionResponse,
    PlanRequest,
    PlanResponse,
    ProfitLossResponse,
    TaxRateResponse,
    TaxRatesRequest,
)

router = APIRouter(tags=["finance"], route_class=DishkaRoute)


@router.get("/expenses")
async def list_expenses(
    params: Annotated[FinanceFilters, Query()], mediator: FromDishka[BaseMediator], user: AuthCurrentUserJWTData
) -> list[ExpenseResponse]:
    return await mediator.handle_query(ListExpensesQuery(user=user, filters=params))


@router.post("/expenses", status_code=status.HTTP_201_CREATED)
async def create_expense(
    request: ExpenseRequest, mediator: FromDishka[BaseMediator], user: AuthCurrentUserJWTData
) -> ExpenseResponse:
    return await mediator.handle_command(
        ManageExpenseCommand(
            user=user, action="create", expense_id=None, payload=request, organization_id=request.organization_id
        )
    )


@router.patch("/expenses/{expense_id}")
async def update_expense(
    expense_id: UUID, request: ExpenseRequest, mediator: FromDishka[BaseMediator], user: AuthCurrentUserJWTData
) -> ExpenseResponse:
    return await mediator.handle_command(
        ManageExpenseCommand(
            user=user, action="update", expense_id=expense_id, payload=request, organization_id=request.organization_id
        )
    )


@router.delete("/expenses/{expense_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_expense(
    expense_id: UUID, organization_id: UUID, mediator: FromDishka[BaseMediator], user: AuthCurrentUserJWTData
) -> Response:
    await mediator.handle_command(
        ManageExpenseCommand(
            user=user, action="delete", expense_id=expense_id, payload=None, organization_id=organization_id
        )
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/tax-rates")
async def get_tax_rates(
    organization_id: UUID, mediator: FromDishka[BaseMediator], user: AuthCurrentUserJWTData
) -> list[TaxRateResponse]:
    return await mediator.handle_query(GetTaxRatesQuery(user=user, organization_id=organization_id))


@router.put("/tax-rates")
async def set_tax_rates(
    request: TaxRatesRequest, mediator: FromDishka[BaseMediator], user: AuthCurrentUserJWTData
) -> list[TaxRateResponse]:
    return await mediator.handle_command(
        SetTaxRatesCommand(user=user, organization_id=request.organization_id, rates=tuple(request.rates))
    )


@router.get("/plans")
async def list_plans(
    organization_id: UUID, mediator: FromDishka[BaseMediator], user: AuthCurrentUserJWTData
) -> list[PlanResponse]:
    return await mediator.handle_query(ListPlansQuery(user=user, organization_id=organization_id))


@router.post("/plans", status_code=status.HTTP_201_CREATED)
async def create_plan(
    request: PlanRequest, mediator: FromDishka[BaseMediator], user: AuthCurrentUserJWTData
) -> PlanResponse:
    return await mediator.handle_command(
        ManagePlanCommand(
            user=user, action="create", plan_id=None, payload=request, organization_id=request.organization_id
        )
    )


@router.patch("/plans/{plan_id}")
async def update_plan(
    plan_id: UUID, request: PlanRequest, mediator: FromDishka[BaseMediator], user: AuthCurrentUserJWTData
) -> PlanResponse:
    return await mediator.handle_command(
        ManagePlanCommand(
            user=user, action="update", plan_id=plan_id, payload=request, organization_id=request.organization_id
        )
    )


@router.delete("/plans/{plan_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_plan(
    plan_id: UUID, organization_id: UUID, mediator: FromDishka[BaseMediator], user: AuthCurrentUserJWTData
) -> Response:
    await mediator.handle_command(
        ManagePlanCommand(user=user, action="delete", plan_id=plan_id, payload=None, organization_id=organization_id)
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/finance/profit-loss")
async def profit_loss(
    params: Annotated[FinanceFilters, Query()], mediator: FromDishka[BaseMediator], user: AuthCurrentUserJWTData
) -> ProfitLossResponse:
    return await mediator.handle_query(ProfitLossQuery(user=user, filters=params))


@router.get("/finance/cash-flow")
async def cash_flow(
    params: Annotated[FinanceFilters, Query()], mediator: FromDishka[BaseMediator], user: AuthCurrentUserJWTData
) -> CashFlowResponse:
    return await mediator.handle_query(CashFlowQuery(user=user, filters=params))


@router.get("/finance/transactions")
async def finance_transactions(
    params: Annotated[FinanceFilters, Query()],
    mediator: FromDishka[BaseMediator],
    user: AuthCurrentUserJWTData,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> PageResult[FinanceTransactionResponse]:
    return await mediator.handle_query(
        FinanceTransactionsQuery(user=user, filters=params, page=page, page_size=page_size)
    )
