from dishka import Provider, Scope, decorate, provide

from app.core.mediators.base import CommandRegistry, QueryRegistry
from app.finance.application import (
    CashFlowHandler,
    CashFlowQuery,
    FinanceTransactionsHandler,
    FinanceTransactionsQuery,
    GetTaxRatesHandler,
    GetTaxRatesQuery,
    ListExpensesHandler,
    ListExpensesQuery,
    ListPlansHandler,
    ListPlansQuery,
    ManageExpenseCommand,
    ManageExpenseHandler,
    ManagePlanCommand,
    ManagePlanHandler,
    ProfitLossHandler,
    ProfitLossQuery,
    SetTaxRatesCommand,
    SetTaxRatesHandler,
)


class FinanceProvider(Provider):
    scope = Scope.REQUEST

    manage_expense = provide(ManageExpenseHandler)
    list_expenses = provide(ListExpensesHandler)
    set_tax_rates = provide(SetTaxRatesHandler)
    get_tax_rates = provide(GetTaxRatesHandler)
    manage_plan = provide(ManagePlanHandler)
    list_plans = provide(ListPlansHandler)
    profit_loss = provide(ProfitLossHandler)
    cash_flow = provide(CashFlowHandler)
    transactions = provide(FinanceTransactionsHandler)

    @decorate
    def commands(self, registry: CommandRegistry) -> CommandRegistry:
        registry.register_command(ManageExpenseCommand, ManageExpenseHandler)
        registry.register_command(SetTaxRatesCommand, SetTaxRatesHandler)
        registry.register_command(ManagePlanCommand, ManagePlanHandler)
        return registry

    @decorate
    def queries(self, registry: QueryRegistry) -> QueryRegistry:
        registry.register_query(ListExpensesQuery, ListExpensesHandler)
        registry.register_query(GetTaxRatesQuery, GetTaxRatesHandler)
        registry.register_query(ListPlansQuery, ListPlansHandler)
        registry.register_query(ProfitLossQuery, ProfitLossHandler)
        registry.register_query(CashFlowQuery, CashFlowHandler)
        registry.register_query(FinanceTransactionsQuery, FinanceTransactionsHandler)
        return registry
