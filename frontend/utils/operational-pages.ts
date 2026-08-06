import { ApiError } from "./api/client";
import { analyticsQuery, financeQuery, resolveOrganizationId } from "./api/query";
import { serverApiRequest } from "./api/server";
import { decimalToString, type CellFormat, type DataStatus, type OperationalViewModel } from "./api/view-models";
import { parseFilters } from "./filters";
import type { AnalyticsOverviewResponse, CabinetResponse, CashFlowResponse, ExpenseResponse, FinanceTransactionResponse, PageResult, ProductGroupResponse, ProductResponse, ProfitLossResponse, SyncOverviewResponse, TaxRateResponse, TimeSeriesResponse } from "./api/generated";

export type { CellFormat, OperationalViewModel as OperationalData };

type RouteConfig = Pick<OperationalViewModel, "title" | "description" | "endpoint">;
const routeConfigs: Record<string, RouteConfig> = {
  "/pulse": { title: "Рука на пульсе", description: "Оперативный мониторинг текущего дня, отклонений и свежести синхронизации.", endpoint: "/api/v1/analytics/overview" },
  "/reports/summary": { title: "Сводный отчёт", description: "Данные аналитики по выбранной организации и кабинетам.", endpoint: "/api/v1/analytics/products" },
  "/products": { title: "Товары", description: "Каталог товаров, доступный выбранной организации.", endpoint: "/api/v1/products" },
  "/products/unit-economics": { title: "Юнит-экономика", description: "Временной ряд метрик unit economics из backend.", endpoint: "/api/v1/analytics/unit-economics" },
  "/products/stocks": { title: "Остатки", description: "Временной ряд складских метрик из backend.", endpoint: "/api/v1/analytics/stocks" },
  "/advertising": { title: "Реклама", description: "Временной ряд рекламных метрик из backend.", endpoint: "/api/v1/analytics/advertising" },
  "/plan-fact": { title: "План-факт", description: "Временной ряд плановых и фактических метрик из backend.", endpoint: "/api/v1/analytics/plan-fact" },
  "/finance/profit-loss": { title: "Прибыли и убытки", description: "Строки P&L за выбранный финансовый период.", endpoint: "/api/v1/finance/profit-loss" },
  "/finance/cash-flow": { title: "Движение денег", description: "Поступления, списания и чистый денежный поток.", endpoint: "/api/v1/finance/cash-flow" },
  "/finance/transactions": { title: "Финансовые операции", description: "Операции с привязкой к кабинету и маркетплейсу.", endpoint: "/api/v1/finance/transactions" },
  "/finance/expenses": { title: "Расходы", description: "Операционные расходы выбранной организации.", endpoint: "/api/v1/expenses" },
  "/management/cabinets": { title: "Кабинеты", description: "Подключения маркетплейсов и scopes credentials.", endpoint: "/api/v1/cabinets" },
  "/management/organizations": { title: "Организации", description: "Рабочие пространства, владельцы и участники.", endpoint: "/api/v1/organizations" },
  "/management/users": { title: "Пользователи", description: "Учётные записи и системные роли пользователей.", endpoint: "/api/v1/users/" },
  "/management/invitations": { title: "Инвайты", description: "Приглашения пользователей в рабочие организации.", endpoint: "/api/v1/organizations/{organization_id}/invitations" },
  "/management/team": { title: "Команда", description: "Участники организации и их роли.", endpoint: "/api/v1/organizations/{organization_id}/members" },
  "/management/taxes": { title: "Налоги", description: "Ставки налогов организации.", endpoint: "/api/v1/tax-rates" },
  "/management/product-groups": { title: "Группы товаров", description: "Группы товаров выбранной организации.", endpoint: "/api/v1/product-groups" },
  "/management/sync": { title: "Синхронизация", description: "Сводка очереди синхронизации маркетплейсов.", endpoint: "/api/v1/sync/overview" },
};

const labels: Record<string, string> = { sales: "Продажи", net_sales: "Чистые продажи", net_profit: "Чистая прибыль", profit: "Прибыль", orders: "Заказы", returns: "Возвраты", advertising: "Реклама", drr: "ДРР", ctr: "CTR", cpc: "CPC", stock: "Остаток" };
const labelFor = (code: string) => labels[code] ?? code;
const statusFor = (warnings: string[]): DataStatus => warnings.length ? "partial" : "fresh";
const base = (path: string): OperationalViewModel => ({ ...routeConfigs[path], path, status: "unknown", metrics: [], columns: [], rows: [], warnings: [] });

function timeSeriesView(path: string, payload: TimeSeriesResponse): OperationalViewModel {
  const view = base(path);
  const codes = Array.from(new Set(payload.points.flatMap((point) => point.metrics.map((metric) => metric.code))));
  view.updated_at = payload.period.date_to;
  view.status = statusFor(payload.warnings);
  view.warnings = payload.warnings.map((message, index) => ({ code: `backend-warning-${index}`, message }));
  view.columns = [{ key: "business_date", label: "Дата", format: "text" }, ...codes.map((code) => ({ key: code, label: labelFor(code), format: "money" as const }))];
  view.rows = payload.points.map((point) => Object.fromEntries([["business_date", point.business_date], ...codes.map((code) => [code, decimalToString(point.metrics.find((metric) => metric.code === code)?.value) || null])]));
  return view;
}

function analyticsMetrics(payload: AnalyticsOverviewResponse): OperationalViewModel["metrics"] { return payload.metrics.map((metric) => ({ label: labelFor(metric.code), value: decimalToString(metric.value), previous: decimalToString(metric.previous_value), delta: decimalToString(metric.delta_percent), format: metric.unit.toLowerCase().includes("percent") ? "percent" : metric.unit.toLowerCase().includes("count") ? "number" : "money" })); }

function overviewView(path: string, payload: AnalyticsOverviewResponse): OperationalViewModel {
  const view = base(path); view.updated_at = payload.data_freshness.map((item) => item.last_success_at).filter((value): value is string => Boolean(value)).sort().at(-1); view.status = statusFor(payload.warnings); view.metrics = analyticsMetrics(payload); view.warnings = payload.warnings.map((message, index) => ({ code: `backend-warning-${index}`, message })); view.columns = [{ key: "cabinet_id", label: "Кабинет", format: "text" }, { key: "last_success_at", label: "Последняя успешная синхронизация", format: "text" }, { key: "complete_through", label: "Данные по", format: "text" }, { key: "missing_kinds", label: "Отсутствующие виды данных", format: "text" }]; view.rows = payload.data_freshness.map((item) => ({ cabinet_id: item.cabinet_id, last_success_at: item.last_success_at ?? null, complete_through: item.complete_through ?? null, missing_kinds: item.missing_kinds.join(", ") || null })); return view;
}

async function organizationQuery(query: string) { return resolveOrganizationId(parseFilters(new URLSearchParams(query))); }

export function getRouteConfig(path: string) { return routeConfigs[path]; }
export type OperationalResult = { data?: OperationalViewModel; error?: ApiError } | { notFound: true };

export async function getOperationalPage(path: string, query = ""): Promise<OperationalResult> {
  if (!routeConfigs[path]) return { notFound: true };
  try {
    if (path === "/pulse") {
      const backendQuery = await analyticsQuery(query);
      return { data: overviewView(path, await serverApiRequest<AnalyticsOverviewResponse>(`/api/v1/analytics/overview?${backendQuery}`)) };
    }
    if (["/reports/summary", "/products/unit-economics", "/products/stocks", "/advertising", "/plan-fact"].includes(path)) {
      const payload = await serverApiRequest<TimeSeriesResponse>(`${routeConfigs[path].endpoint}?${await analyticsQuery(query)}`);
      return { data: timeSeriesView(path, payload) };
    }
    if (path === "/products") {
      const organizationId = await organizationQuery(query); const payload = await serverApiRequest<PageResult<ProductResponse>>(`/api/v1/products?organization_id=${organizationId}&page=1&page_size=100`); const view = base(path); view.status = "fresh"; view.columns = [{ key: "name", label: "Название", format: "text" }, { key: "internal_sku", label: "SKU", format: "text" }, { key: "brand", label: "Бренд", format: "text" }, { key: "category", label: "Категория", format: "text" }, { key: "group_id", label: "Группа", format: "text" }]; view.rows = payload.items.map((item) => ({ name: item.name, internal_sku: item.internal_sku, brand: item.brand ?? null, category: item.category ?? null, group_id: item.group_id ?? null })); return { data: view };
    }
    if (path === "/management/cabinets") {
      const payload = await serverApiRequest<PageResult<CabinetResponse>>("/api/v1/cabinets?page=1&page_size=100"); const view = base(path); view.status = "fresh"; view.columns = [{ key: "name", label: "Название", format: "text" }, { key: "marketplace", label: "Маркетплейс", format: "text" }, { key: "external_id", label: "Внешний ID", format: "text" }, { key: "is_active", label: "Активен", format: "status" }, { key: "credential_scopes", label: "Scopes", format: "text" }, { key: "credential_validated_at", label: "Ключ проверен", format: "text" }]; view.rows = payload.items.map((item) => ({ name: item.name, marketplace: item.marketplace, external_id: item.external_id, is_active: item.is_active ? "активен" : "неактивен", credential_scopes: item.credential_scopes.join(", "), credential_validated_at: item.credential_validated_at ?? null })); return { data: view };
    }
    if (["/management/organizations", "/management/users", "/management/invitations"].includes(path)) {
      const view = base(path); view.status = "fresh"; return { data: view };
    }
    if (path === "/management/team") {
      const organizationId = await organizationQuery(query); const payload = await serverApiRequest<PageResult<import("./api/generated").MemberResponse>>(`/api/v1/organizations/${organizationId}/members?page=1&page_size=100`); const view = base(path); view.status = "fresh"; view.columns = [{ key: "user_id", label: "Пользователь", format: "text" }, { key: "role", label: "Роль", format: "text" }, { key: "is_active", label: "Активен", format: "status" }]; view.rows = payload.items.map((item) => ({ user_id: item.user_id, role: item.role, is_active: item.is_active ? "активен" : "неактивен" })); return { data: view };
    }
    if (path === "/management/product-groups") {
      const organizationId = await organizationQuery(query); const payload = await serverApiRequest<ProductGroupResponse[]>(`/api/v1/product-groups?organization_id=${organizationId}`); const view = base(path); view.status = "fresh"; view.columns = [{ key: "name", label: "Название", format: "text" }, { key: "id", label: "ID", format: "text" }]; view.rows = payload.map((item) => ({ name: item.name, id: item.id })); return { data: view };
    }
    if (path === "/management/sync") {
      const payload = await serverApiRequest<SyncOverviewResponse>("/api/v1/sync/overview"); const view = base(path); view.status = payload.failed > 0 ? "partial" : "fresh"; view.columns = [{ key: "status", label: "Статус", format: "text" }, { key: "count", label: "Количество", format: "number" }]; view.rows = [{ status: "queued", count: payload.queued }, { status: "running", count: payload.running }, { status: "retry_wait", count: payload.retry_wait }, { status: "paused", count: payload.paused }, { status: "failed", count: payload.failed }]; return { data: view };
    }
    if (path === "/finance/profit-loss") {
      const payload = await serverApiRequest<ProfitLossResponse>(`/api/v1/finance/profit-loss?${await financeQuery(query)}`); const view = base(path); view.updated_at = payload.period_to; view.status = statusFor(payload.warnings); view.warnings = payload.warnings.map((message, index) => ({ code: `backend-warning-${index}`, message })); view.columns = [{ key: "code", label: "Статья", format: "text" }, { key: "value", label: "Значение", format: "money" }]; view.rows = payload.lines.map((line) => ({ code: labelFor(line.code), value: decimalToString(line.value) })); return { data: view };
    }
    if (path === "/finance/cash-flow") {
      const payload = await serverApiRequest<CashFlowResponse>(`/api/v1/finance/cash-flow?${await financeQuery(query)}`); const view = base(path); view.status = "fresh"; view.columns = [{ key: "code", label: "Показатель", format: "text" }, { key: "value", label: "Значение", format: "money" }]; view.rows = [{ code: "Поступления", value: decimalToString(payload.inflow) }, { code: "Списания", value: decimalToString(payload.outflow) }, { code: "Чистый денежный поток", value: decimalToString(payload.net_cash_flow) }]; return { data: view };
    }
    if (path === "/finance/transactions") {
      const payload = await serverApiRequest<PageResult<FinanceTransactionResponse>>(`/api/v1/finance/transactions?${await financeQuery(query)}&page=1&page_size=100`); const view = base(path); view.status = "fresh"; view.columns = [{ key: "business_date", label: "Дата", format: "text" }, { key: "marketplace", label: "Маркетплейс", format: "text" }, { key: "operation_type", label: "Операция", format: "text" }, { key: "amount", label: "Сумма", format: "money" }, { key: "external_key", label: "Внешний ключ", format: "text" }]; view.rows = payload.items.map((item) => ({ business_date: item.business_date, marketplace: item.marketplace, operation_type: item.operation_type, amount: decimalToString(item.amount), external_key: item.external_key })); return { data: view };
    }
    if (path === "/finance/expenses") {
      const payload = await serverApiRequest<ExpenseResponse[]>(`/api/v1/expenses?${await financeQuery(query)}`); const view = base(path); view.status = "fresh"; view.columns = [{ key: "business_date", label: "Дата", format: "text" }, { key: "category_id", label: "Категория", format: "text" }, { key: "amount", label: "Сумма", format: "money" }, { key: "description", label: "Описание", format: "text" }]; view.rows = payload.map((item) => ({ business_date: item.business_date, category_id: item.category_id, amount: decimalToString(item.amount), description: item.description ?? null })); return { data: view };
    }
    if (path === "/management/taxes") {
      const organizationId = await organizationQuery(query); const payload = await serverApiRequest<TaxRateResponse[]>(`/api/v1/tax-rates?organization_id=${organizationId}`); const view = base(path); view.status = "fresh"; view.columns = [{ key: "valid_from", label: "Действует с", format: "text" }, { key: "valid_to", label: "Действует до", format: "text" }, { key: "rate_percent", label: "Ставка", format: "percent" }, { key: "base_metric", label: "База", format: "text" }]; view.rows = payload.map((item) => ({ valid_from: item.valid_from, valid_to: item.valid_to ?? null, rate_percent: decimalToString(item.rate_percent), base_metric: item.base_metric })); return { data: view };
    }
    throw new ApiError("Маршрут backend не настроен", 404, "ROUTE_NOT_CONFIGURED");
  } catch (error) { return { error: error instanceof ApiError ? error : new ApiError("Не удалось загрузить данные отчёта", 500) }; }
}
