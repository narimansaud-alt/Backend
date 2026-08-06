"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { Loader2, PackageSearch } from "lucide-react";
import { useEffect, useState } from "react";
import { apiRequest, ApiError } from "@/utils/api/client";
import { backendFiltersQuery, defaultDateRange, parseFilters, toBackendAnalyticsFilters } from "@/utils/filters";
import { decimalToString, type DashboardViewModel, type DataStatus, type MetricViewModel } from "@/utils/api/view-models";
import type { AnalyticsOverviewResponse, CabinetResponse, MetricResponse, OrganizationResponse, PageResult, TimeSeriesResponse } from "@/utils/api/generated";
import { DashboardView } from "./dashboard-view";
import { DataError } from "@/components/ui/data-state";

const labels: Record<string, string> = {
  net_profit: "Чистая прибыль", net_sales: "Чистые продажи", sales: "Продажи", orders: "Заказы", returns: "Возвраты",
  buyout_rate: "Процент выкупа", commission: "Комиссия", logistics: "Логистика", storage: "Хранение", advertising: "Реклама",
  drr: "ДРР", cost: "Себестоимость", taxes: "Налоги", operating_expenses: "Операционные расходы", roi: "ROI", average_check: "Средний чек",
};

function metricUnit(value: string): "rub" | "percent" | "count" {
  const normalized = value.toLowerCase();
  return normalized.includes("percent") || normalized.includes("rate") || normalized === "%" ? "percent" : normalized.includes("count") || normalized.includes("quantity") ? "count" : "rub";
}

function metricView(metric: MetricResponse): MetricViewModel {
  return { id: metric.code, label: labels[metric.code] ?? metric.code, value: decimalToString(metric.value), previous: decimalToString(metric.previous_value), absolute_delta: decimalToString(metric.delta), relative_delta: decimalToString(metric.delta_percent), unit: metricUnit(metric.unit), change_direction: ["returns", "commission", "logistics", "storage", "advertising", "drr", "cost", "taxes", "operating_expenses"].includes(metric.code) ? "lower_is_better" : "higher_is_better", status: metric.status as DataStatus };
}

function adapt(overview: AnalyticsOverviewResponse, timeseries: TimeSeriesResponse): DashboardViewModel {
  const warnings = overview.warnings.map((message, index) => ({ code: `backend-warning-${index}`, message }));
  return {
    updated_at: overview.data_freshness.map((item) => item.last_success_at).filter((value): value is string => Boolean(value)).sort().at(-1),
    status: warnings.length ? "partial" : "fresh",
    metrics: overview.metrics.map(metricView),
    timeseries: timeseries.points.map((point) => ({ date: point.business_date, sales: decimalToString(point.metrics.find((metric) => ["sales", "net_sales"].includes(metric.code))?.value), profit: decimalToString(point.metrics.find((metric) => ["profit", "net_profit"].includes(metric.code))?.value), orders: Number(decimalToString(point.metrics.find((metric) => ["orders", "order_count"].includes(metric.code))?.value)) || 0 })),
    marketplaces: [], warnings, expense_structure: [], product_rows: [], waterfall: [],
  };
}

function EmptyCabinetsState() {
  return <section className="panel grid min-h-[360px] place-items-center p-8 text-center"><div className="max-w-md"><span className="mx-auto grid size-11 place-items-center rounded-full bg-[#edf6d7] text-[#34745f]"><PackageSearch size={21} /></span><h2 className="mt-4 text-base font-semibold">Нет подключённых кабинетов</h2><p className="mt-2 text-sm leading-6 text-[#747a73]">Сначала подключите кабинет маркетплейса. После синхронизации здесь появятся продажи, прибыль и остатки.</p><Link href="/management/cabinets" className="primary-button mt-5">Подключить кабинет</Link></div></section>;
}

export function DashboardLoader({ initialData }: { initialData?: DashboardViewModel }) {
  const search = useSearchParams();
  const [data, setData] = useState(initialData);
  const [error, setError] = useState<ApiError>();
  const [hasCabinets, setHasCabinets] = useState<boolean | undefined>();

  useEffect(() => {
    let active = true;
    const filters = { ...defaultDateRange(), ...parseFilters(search) };
    Promise.resolve().then(async () => {
      const [organizationPage, cabinetPage] = await Promise.all([
        apiRequest<PageResult<OrganizationResponse>>("/api/v1/organizations?page=1&page_size=1"),
        apiRequest<PageResult<CabinetResponse>>("/api/v1/cabinets?page=1&page_size=100"),
      ]);
      const organization = organizationPage.items[0];
      if (!organization) throw new ApiError("Сначала создайте организацию.", 422, "ORGANIZATION_REQUIRED");
      const query = backendFiltersQuery(toBackendAnalyticsFilters(filters, organization.id));
      const [overview, timeseries] = await Promise.all([
        apiRequest<AnalyticsOverviewResponse>(`/api/v1/analytics/overview?${query}`),
        apiRequest<TimeSeriesResponse>(`/api/v1/analytics/timeseries?${query}`),
      ]);
      if (!active) return;
      setHasCabinets(cabinetPage.items.length > 0);
      setData(adapt(overview, timeseries));
      setError(undefined);
    }).catch((value) => { if (active) setError(value instanceof ApiError ? value : new ApiError("Не удалось загрузить dashboard", 500)); });
    return () => { active = false; };
  }, [search]);

  if (error) return <DataError message={error.message} status={error.status} code={error.code} requestId={error.requestId} />;
  if (hasCabinets === false) return <EmptyCabinetsState />;
  if (!data) return <div className="panel grid min-h-[360px] place-items-center"><Loader2 className="animate-spin text-[#34745f]" size={24} /></div>;
  return <DashboardView data={data} />;
}
