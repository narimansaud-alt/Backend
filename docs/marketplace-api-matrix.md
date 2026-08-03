# Marketplace API matrix

Checked against vendor documentation on 2026-08-03. Limits are enforced per
marketplace, cabinet, and endpoint group. Vendor documentation remains the
runtime source of truth; method-specific limits can change without a version
bump and must be revalidated before enabling a new sync kind in production.

| Marketplace / kind | Official method | Scope | Pagination / window | Stable key and notes |
|---|---|---|---|---|
| WB orders | `GET statistics-api.wildberries.ru/api/v1/supplier/orders` | Statistics | `dateFrom=lastChangeDate`; about 80k rows; history guaranteed 90 days; 1 req/min | `srid`; preliminary, refresh ~30 min |
| WB sales/returns | `GET statistics-api.wildberries.ru/api/v1/supplier/sales` | Statistics | same `lastChangeDate` cursor and 90-day history; 1 req/min | `srid` plus sale/return identity; finance must reconcile to realization report |
| WB finance | `GET statistics-api.wildberries.ru/api/v5/supplier/reportDetailByPeriod` | Statistics | date range plus vendor pagination; 1 req/min; data since 2024-01-29 | report line identity (`rrd_id` when supplied) |
| WB funnel | `POST seller-analytics-api.wildberries.ru/api/analytics/v3/sales-funnel/products` | Analytics | maximum 365 days | `nmID` + period; hourly freshness |
| WB funnel daily | `POST .../api/analytics/v3/sales-funnel/products/history` | Analytics | maximum 7 days | `nmID` + `dt` |
| WB stocks | `POST .../api/analytics/v1/stocks-report/wb-warehouses` | Analytics | current snapshot; 3 req/min | `nmID` + warehouse + size + snapshot date |
| Ozon postings | `POST api-seller.ozon.ru/v3/posting/fbs/list` and FBO equivalent selected by scheme | Seller API key + Client-Id | offset/limit, RFC3339 filter; exact caps from live OpenAPI | posting number + product/SKU |
| Ozon finance | `POST api-seller.ozon.ru/v3/finance/transaction/list` | Seller API key + Client-Id | page/page_size; max one calendar month | `operation_id` + item/service dimension |
| Ozon stocks | `POST api-seller.ozon.ru/v2/analytics/stock_on_warehouses` | Seller API key + Client-Id | offset/limit; exact caps from live OpenAPI | SKU/offer + warehouse + snapshot date |
| Yandex orders | `POST api.partner.market.yandex.ru/v1/businesses/{businessId}/orders` | order read or all-methods read | `pageToken`/`limit`; max 30 days; 10k req/hour | order id + item/shopSku; preferred over deprecated campaign list |
| Yandex order stats | `POST .../v2/campaigns/{campaignId}/stats/orders` | order read or all-methods read | `pageToken`; up to 200 orders/request; 10k req/hour | order id + item/shopSku; up to ~40 min delay |
| Yandex returns | `GET .../v2/campaigns/{campaignId}/returns` | order read | `pageToken`/`limit` | return id + item |
| Yandex reports | generate endpoint for the selected report, then `GET .../v2/reports/info/{reportId}` | finance/order scope varies | asynchronous report; plan-specific generation limits | report id then document row identity |

Yandex permits at most four concurrent calls for the relevant campaign,
business, or account and may return HTTP 420 for rate limiting. New pagination
uses opaque `pageToken`; the legacy numeric `page` form is not used when both
are available. Ozon's documentation is rendered from a live OpenAPI portal, so
connector activation performs a capability check and keeps unverified kinds
disabled instead of guessing paths or limits.
