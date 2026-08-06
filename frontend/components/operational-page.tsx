import { AlertTriangle, ArrowDownRight, ArrowUpRight, Info, LockKeyhole } from "lucide-react";
import { formatDateTime, formatMetric } from "@/utils/formatters";
import { FilterBar } from "./dashboard/filter-bar";
import { DataTable } from "./ui/data-table";
import { RouteAction } from "./ui/route-action";
import { PageHeader } from "./ui/page-header";
import type { OperationalData } from "@/utils/operational-pages";
import { TeamManagement } from "./management/team-management";
import { CabinetManagement } from "./management/cabinet-management";

export function OperationalPage({ data }: { data: OperationalData }) {
  const management = data.path.startsWith("/management/");
  const formatValue = (value: string, format: "money" | "percent" | "number" | "text") => format === "text" ? value : formatMetric(value, format === "money" ? "rub" : format === "percent" ? "percent" : "count");
  if (data.path === "/management/team" || data.path === "/management/cabinets") return <div className="mx-auto max-w-[1680px]"><PageHeader title={data.title} description={data.description} actions={false} />{data.path === "/management/team" ? <TeamManagement /> : <CabinetManagement />}</div>;
  return <div className="mx-auto max-w-[1680px]">
    <PageHeader title={data.title} description={data.description} updated={data.updated_at ? formatDateTime(data.updated_at) : undefined} actions={!management} />
    {!management && <FilterBar />}
    {data.warnings?.map((warning) => <div key={warning.code} className="mt-3 flex items-start gap-3 rounded-md border border-[#ead8bd] bg-[#fffaf2] p-3 text-xs text-[#6f542e]" role="status"><AlertTriangle size={16} className="shrink-0" /><span>{warning.message}{warning.action_href?.startsWith("/") && !warning.action_href.startsWith("//") && <a href={warning.action_href} className="ml-2 font-semibold underline">{warning.action_label ?? "Открыть"}</a>}</span></div>)}
    {data.path === "/pulse" && <div className="mt-4 flex gap-3 rounded-md border border-[#cde1d8] bg-[#f4faf7] p-3 text-xs text-[#2b5f4d]"><Info size={16} className="shrink-0" /><span>Сравнение текущего дня выполняется backend только по одинаковому времени среза. Статус текущего дня: <b>{data.status}</b>.</span></div>}
    {data.path === "/advertising" && data.status !== "fresh" && <div className="mt-4 flex gap-3 rounded-md border border-[#ead8bd] bg-[#fffaf2] p-3 text-xs text-[#6f542e]"><AlertTriangle size={16} className="shrink-0" /><span>Рекламные данные доступны не полностью. Проверьте scopes кабинета и синхронизацию.</span></div>}
    {data.path === "/management/team" && <div className="mt-4 flex gap-3 rounded-md border border-[#dfe2dc] bg-white p-3 text-xs text-[#616760]"><LockKeyhole size={16} className="shrink-0" /><span>Backend повторно проверяет права и cabinet scope для каждого запроса.</span></div>}
    <section className="mt-4 grid gap-2 sm:grid-cols-2 xl:grid-cols-4">{data.metrics.map((metric) => { const positive = !metric.delta?.trim().startsWith("-"); const Icon = positive ? ArrowUpRight : ArrowDownRight; return <article key={metric.label} className="kpi-card"><div className="text-xs font-medium text-[#6d726c]">{metric.label}</div><div className="mt-3 text-[21px] font-semibold tabular-nums">{formatValue(metric.value, metric.format)}</div>{metric.delta && <div className={`delta mt-3 w-fit ${positive ? "delta-good" : "delta-bad"}`}><Icon size={13} />{metric.delta}</div>}</article>; })}</section>
    <section className="panel mt-4 overflow-hidden"><div className="flex flex-wrap items-center justify-between gap-2 border-b border-[#e5e7e2] px-4 py-3"><div><h2 className="section-title">{management ? "Состояние и история" : "Детализация"}</h2><p className="mt-1 text-[11px] text-[#858b84]">Данные и статусы предоставлены backend.</p></div>{management && <RouteAction path={data.path} />}</div><DataTable columns={data.columns} rows={data.rows} emptyMessage={data.empty_message} /></section>
  </div>;
}
