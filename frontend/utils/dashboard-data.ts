import { ApiError } from "./api/client";
import { analyticsQuery } from "./api/query";
import { serverApiRequest } from "./api/server";
import { decimalToString } from "./api/view-models";
import type { AnalyticsOverviewResponse, MetricResponse, TimeSeriesResponse } from "./api/generated";
import type { DashboardViewModel, DataStatus, MetricViewModel } from "./api/view-models";

const labels: Record<string, string> = {
  net_profit: "Чистая прибыль", net_sales: "Чистые продажи", sales: "Продажи", orders: "Заказы", returns: "Возвраты",
  buyout_rate: "Процент выкупа", commission: "Комиссия", logistics: "Логистика", storage: "Хранение", advertising: "Реклама",
  drr: "ДРР", cost: "Себестоимость", taxes: "Налоги", operating_expenses: "Операционные расходы", roi: "ROI", average_check: "Средний чек",
};
const lowerIsBetter = new Set(["returns", "commission", "logistics", "storage", "advertising", "drr", "cost", "taxes", "operating_expenses"]);

function status(value: string): DataStatus { return value === "fresh" || value === "stale" || value === "partial" ? value : "unknown"; }
function unit(value: string): "rub" | "percent" | "count" { const normalized = value.toLowerCase(); return normalized.includes("percent") || normalized.includes("rate") || normalized === "%" ? "percent" : normalized.includes("count") || normalized.includes("quantity") ? "count" : "rub"; }
function metricView(metric: MetricResponse): MetricViewModel { return { id: metric.code, label: labels[metric.code] ?? metric.code, value: decimalToString(metric.value), previous: decimalToString(metric.previous_value), absolute_delta: decimalToString(metric.delta), relative_delta: decimalToString(metric.delta_percent), unit: unit(metric.unit), change_direction: lowerIsBetter.has(metric.code) ? "lower_is_better" : "higher_is_better", status: status(metric.status) }; }
function metricValue(point: { code: string; value: string | number | null }[], codes: string[]) { const found = point.find((metric) => codes.includes(metric.code)); return decimalToString(found?.value); }

function adaptOverview(overview: AnalyticsOverviewResponse, timeseries: TimeSeriesResponse): DashboardViewModel {
  const freshnessWarnings = overview.data_freshness.flatMap((item) => item.missing_kinds.map((kind) => `Для кабинета ${item.cabinet_id} отсутствуют данные: ${kind}.`));
  const warnings = [...overview.warnings, ...freshnessWarnings].map((message, index) => ({ code: `backend-warning-${index}`, message }));
  const updatedAt = overview.data_freshness.map((item) => item.last_success_at).filter((value): value is string => Boolean(value)).sort().at(-1);
  const points = timeseries.points.map((point) => ({ date: point.business_date, sales: metricValue(point.metrics, ["sales", "net_sales"]), profit: metricValue(point.metrics, ["profit", "net_profit"]), orders: Number(metricValue(point.metrics, ["orders", "order_count"])) || 0 }));
  const overallStatus: DataStatus = warnings.length ? "partial" : overview.metrics.some((metric) => status(metric.status) === "stale") ? "stale" : "fresh";
  return { updated_at: updatedAt, status: overallStatus, metrics: overview.metrics.map(metricView), timeseries: points, marketplaces: [], warnings, expense_structure: [], product_rows: [], waterfall: [] };
}

export type DashboardResult = { data?: DashboardViewModel; error?: ApiError };

export async function getOverview(query = ""): Promise<DashboardResult> {
  try {
    const backendQuery = await analyticsQuery(query);
    const [overview, timeseries] = await Promise.all([
      serverApiRequest<AnalyticsOverviewResponse>(`/api/v1/analytics/overview?${backendQuery}`),
      serverApiRequest<TimeSeriesResponse>(`/api/v1/analytics/timeseries?${backendQuery}`),
    ]);
    return { data: adaptOverview(overview, timeseries) };
  } catch (error) {
    return { error: error instanceof ApiError ? error : new ApiError("Не удалось загрузить отчёт", 500) };
  }
}
