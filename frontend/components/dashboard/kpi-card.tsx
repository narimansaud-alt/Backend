import { ArrowDownRight, ArrowUpRight, CircleHelp } from "lucide-react";
import type { MetricViewModel } from "@/utils/api/view-models";
import { formatMetric } from "@/utils/formatters";

export function KpiCard({ metric }: { metric: MetricViewModel }) {
  const delta = metric.absolute_delta;
  const relative = metric.relative_delta;
  const improved = metric.change_direction === "higher_is_better" ? !relative?.startsWith("-") : relative?.startsWith("-");
  const Direction = relative?.startsWith("-") ? ArrowDownRight : ArrowUpRight;
  return <article className="kpi-card">
    <div className="flex items-center justify-between gap-2"><h3 className="truncate text-xs font-medium text-[#6d726c]">{metric.label}</h3><span className="group relative"><CircleHelp size={14} className="text-[#a0a59e]" aria-label="Формула и источник доступны в подсказке" /><span className="tooltip">Метрика и её формула рассчитаны backend по финансовым правилам. Текущий статус: {metric.status}.</span></span></div>
    <div className="mt-3 truncate text-[21px] font-semibold tabular-nums tracking-[-.02em]">{formatMetric(metric.value, metric.unit)}</div>
    <div className="mt-3 flex items-center justify-between gap-2"><span className={`delta ${improved ? "delta-good" : "delta-bad"}`}><Direction size={13} />{relative ?? "—"}{relative && !relative.endsWith("%") ? "%" : ""}</span><span className="truncate text-[10px] tabular-nums text-[#929790]">было {formatMetric(metric.previous, metric.unit)}</span></div>
    {delta && <p className="mt-1 text-[10px] text-[#858b84]">Изменение: {formatMetric(delta, metric.unit)}</p>}
    {metric.status !== "fresh" && <span className="mt-2 block text-[10px] text-[#9b5d28]">{metric.status === "partial" ? "Неполные данные" : "Данные устарели"}</span>}
  </article>;
}
