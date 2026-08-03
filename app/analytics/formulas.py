from dataclasses import dataclass, fields
from decimal import Decimal

ZERO = Decimal("0")
HUNDRED = Decimal("100")


def safe_ratio(numerator: Decimal, denominator: Decimal, *, percent: bool = False) -> Decimal | None:
    if denominator == ZERO:
        return None
    value = numerator / denominator
    return value * HUNDRED if percent else value


@dataclass(frozen=True)
class MetricInputs:
    orders_amount: Decimal = ZERO
    orders_qty: Decimal = ZERO
    sales_amount: Decimal = ZERO
    sales_qty: Decimal = ZERO
    returns_amount: Decimal = ZERO
    returns_qty: Decimal = ZERO
    marketplace_commission: Decimal = ZERO
    logistics: Decimal = ZERO
    storage: Decimal = ZERO
    acquiring: Decimal = ZERO
    penalties: Decimal = ZERO
    other_deductions: Decimal = ZERO
    compensations: Decimal = ZERO
    advertising_cost: Decimal = ZERO
    cogs: Decimal = ZERO
    tax: Decimal = ZERO
    operating_expenses: Decimal = ZERO
    stock_value: Decimal = ZERO
    impressions: Decimal = ZERO
    clicks: Decimal = ZERO
    add_to_cart: Decimal = ZERO
    ad_orders: Decimal = ZERO
    ad_sales: Decimal = ZERO


def calculate_metrics(values: MetricInputs) -> dict[str, Decimal | None]:
    result: dict[str, Decimal | None] = {field.name: getattr(values, field.name) for field in fields(values)}
    net_sales = values.sales_amount - values.returns_amount
    gross_profit = (
        net_sales
        - values.marketplace_commission
        - values.logistics
        - values.storage
        - values.acquiring
        - values.other_deductions
        + values.compensations
        - values.cogs
    )
    operating_profit = gross_profit - values.advertising_cost - values.operating_expenses - values.penalties
    net_profit = operating_profit - values.tax
    result.update(
        {
            "net_sales": net_sales,
            "buyout_rate": safe_ratio(values.sales_qty, values.orders_qty, percent=True),
            "average_order_value": safe_ratio(net_sales, values.sales_qty),
            "gross_profit": gross_profit,
            "operating_profit": operating_profit,
            "net_profit": net_profit,
            "margin": safe_ratio(net_profit, net_sales, percent=True),
            "drr": safe_ratio(values.advertising_cost, net_sales, percent=True),
            "roi": safe_ratio(net_profit, values.cogs, percent=True),
            "ctr": safe_ratio(values.clicks, values.impressions, percent=True),
            "cpc": safe_ratio(values.advertising_cost, values.clicks),
            "conversion_rate": safe_ratio(values.ad_orders, values.clicks, percent=True),
        }
    )
    return result
