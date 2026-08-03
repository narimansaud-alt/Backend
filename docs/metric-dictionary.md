# Metric dictionary

All currency values are `Decimal` in cabinet currency (RUB by default). The
serving grain is `(organization_id, cabinet_id, product_id, business_date)`.
Ratios return `null` when the denominator is zero. Facts remain traceable by
their marketplace external key.

| Code | Formula / source | Sign and missing-data policy |
|---|---|---|
| `orders_amount` | sum order fact amount | Positive; operational data |
| `orders_qty` | sum order fact quantity | Positive; operational data |
| `sales_amount` | sum completed sale amount | Positive |
| `sales_qty` | sum completed sale quantity | Positive |
| `returns_amount` | absolute sum return amount | Positive deduction |
| `returns_qty` | absolute sum return quantity | Positive deduction |
| `net_sales` | `sales_amount - returns_amount` | Can be negative |
| `buyout_rate` | `sales_qty / orders_qty * 100` | `null` if no orders |
| `average_order_value` | `net_sales / sales_qty` | `null` if no sales |
| `marketplace_commission` | canonical finance operations | Positive deduction |
| `logistics` | canonical finance operations | Positive deduction |
| `storage` | canonical finance operations | Positive deduction |
| `acquiring` | canonical finance operations | Positive deduction |
| `penalties` | canonical finance operations | Positive deduction |
| `other_deductions` | unmapped seller deductions | Positive deduction; warning |
| `compensations` | marketplace compensation operations | Positive addition |
| `advertising_cost` | advertising facts | Positive deduction; warning if unavailable |
| `cogs` | sold quantity × cost effective on sale date | Warning and partial coverage if absent |
| `tax` | configured period rate/base | Positive deduction; zero only if explicitly configured |
| `operating_expenses` | allocated operating expenses | Positive deduction |
| `gross_profit` | `net_sales - commission - logistics - storage - acquiring - other_deductions + compensations - cogs` | Partial if cost/finance missing |
| `operating_profit` | `gross_profit - advertising_cost - operating_expenses - penalties` | Partial if advertising missing |
| `net_profit` | `operating_profit - tax` | Partial if tax missing |
| `margin` | `net_profit / net_sales * 100` | `null` if net sales is zero |
| `drr` | `advertising_cost / net_sales * 100` | `null` if net sales is zero |
| `roi` | `net_profit / cogs * 100` | `null` if COGS is zero |
| `stock_value` | closing quantity × effective cost | Partial if cost missing |
| `days_of_stock` | closing quantity / average daily sales qty | `null` if velocity is zero |
| `turnover_days` | average stock / COGS × period days | `null` if COGS is zero |
| `gmroi` | gross profit / average stock value | `null` if stock value is zero |
| `ctr` | `clicks / impressions * 100` | `null` if no impressions |
| `cpc` | `advertising_cost / clicks` | `null` if no clicks |
| `conversion_rate` | `ad_orders / clicks * 100` | `null` if no clicks |
| `variance` | `actual - plan` | Same unit as plan |
| `completion_percent` | `actual / plan * 100` | `null` if plan is zero |
| `forecast` | `actual / elapsed_days × period_days` | `null` before period starts |

Custom metrics accept only literals, known metric identifiers, parentheses, and
`+ - * /`. They are parsed to an AST with bounded depth; neither Python `eval`
nor user-provided SQL is used.

