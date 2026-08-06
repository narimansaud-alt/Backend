"use client";

import { useEffect, useMemo, useState } from "react";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { CalendarDays, ChevronDown, Loader2, RotateCcw, SlidersHorizontal } from "lucide-react";
import { apiRequest } from "@/utils/api/client";
import { activeFilterCount, defaultDateRange, moscowDate, parseFilters, serializeFilters, type FilterState } from "@/utils/filters";
import type { CabinetResponse, Marketplace, OrganizationResponse, PageResult } from "@/utils/api/generated";

const marketplaceOptions = [
  ["wildberries", "Wildberries"],
  ["ozon", "Ozon"],
  ["yandex_market", "Яндекс Маркет"],
] as const;

const defaults = (): FilterState => defaultDateRange();

export function FilterBar() {
  const pathname = usePathname();
  const search = useSearchParams();
  const router = useRouter();
  const initial = useMemo(() => ({ ...defaults(), ...parseFilters(search) }), [search]);
  const [draft, setDraft] = useState<FilterState>(initial);
  const [expanded, setExpanded] = useState(false);
  const [organizations, setOrganizations] = useState<OrganizationResponse[]>([]);
  const [cabinets, setCabinets] = useState<CabinetResponse[]>([]);
  const [loadingOptions, setLoadingOptions] = useState(false);

  useEffect(() => setDraft(initial), [initial]);
  useEffect(() => {
    let active = true;
    setLoadingOptions(true);
    Promise.all([
      apiRequest<PageResult<OrganizationResponse>>("/api/v1/organizations?page=1&page_size=100"),
      apiRequest<PageResult<CabinetResponse>>("/api/v1/cabinets?page=1&page_size=100"),
    ]).then(([organizationPage, cabinetPage]) => {
      if (!active) return;
      setOrganizations(organizationPage.items);
      setCabinets(cabinetPage.items);
    }).catch(() => undefined).finally(() => { if (active) setLoadingOptions(false); });
    return () => { active = false; };
  }, []);

  const count = activeFilterCount(draft);
  const apply = (next = draft) => {
    const query = serializeFilters(next).toString();
    router.replace(query ? `${pathname}?${query}` : pathname, { scroll: false });
  };
  const reset = () => { const next = defaults(); setDraft(next); apply(next); };
  const set = (key: keyof FilterState, value: string | string[] | undefined) => setDraft((current) => ({ ...current, [key]: value && (!Array.isArray(value) || value.length) ? value : undefined }));
  const toggleMarket = (value: Marketplace) => {
    const current = draft.marketplaces ?? [];
    set("marketplaces", current.includes(value) ? current.filter((item) => item !== value) : [...current, value]);
  };
  const selectedOrganization = draft.organization_ids?.[0];
  const availableCabinets = selectedOrganization ? cabinets.filter((cabinet) => cabinet.organization_id === selectedOrganization) : cabinets;

  return (
    <section className="filter-panel" aria-label="Фильтры отчёта">
      <div className="flex flex-wrap items-center gap-2">
        <div className="filter-control w-full sm:w-auto">
          <CalendarDays size={15} aria-hidden="true" />
          <input type="date" aria-label="Дата начала" value={draft.date_from ?? ""} onChange={(event) => set("date_from", event.target.value)} />
          <span className="text-[#a0a59e]" aria-hidden="true">—</span>
          <input type="date" aria-label="Дата окончания" value={draft.date_to ?? ""} onChange={(event) => set("date_to", event.target.value)} />
        </div>
        <select className="filter-control appearance-none pr-8" defaultValue="30" onChange={(event) => {
          const value = event.target.value;
          const ranges: Record<string, FilterState> = {
            today: { date_from: moscowDate(), date_to: moscowDate() },
            yesterday: { date_from: moscowDate(-1), date_to: moscowDate(-1) },
            "7": { date_from: moscowDate(-6), date_to: moscowDate() },
            "30": defaults(),
          };
          if (ranges[value]) setDraft((current) => ({ ...current, ...ranges[value] }));
        }} aria-label="Период">
          <option value="today">Сегодня</option><option value="yesterday">Вчера</option><option value="7">Последние 7 дней</option><option value="30">Последние 30 дней</option>
        </select>
        <button className="filter-control" onClick={() => setExpanded((value) => !value)} aria-expanded={expanded}><SlidersHorizontal size={15} />Фильтры{count > 0 && <span className="count-badge">{count}</span>}<ChevronDown size={14} /></button>
        <div className="ml-auto flex items-center gap-2"><button className="icon-button" onClick={reset} aria-label="Сбросить фильтры" title="Сбросить фильтры"><RotateCcw size={15} /></button><button className="primary-button" onClick={() => apply()}>Применить</button></div>
      </div>
      {expanded && <div className="mt-3 grid gap-3 border-t border-[#e5e7e2] pt-3 sm:grid-cols-2 xl:grid-cols-4">
        <label className="field-label">Организация<select value={selectedOrganization ?? "all"} onChange={(event) => { const organizationId = event.target.value === "all" ? undefined : event.target.value; set("organization_ids", organizationId ? [organizationId] : undefined); set("cabinet_ids", undefined); }} disabled={loadingOptions}><option value="all">Все организации</option>{organizations.map((organization) => <option key={organization.id} value={organization.id}>{organization.name}</option>)}</select></label>
        <label className="field-label">Кабинет<select value={draft.cabinet_ids?.[0] ?? "all"} onChange={(event) => set("cabinet_ids", event.target.value === "all" ? undefined : [event.target.value])} disabled={loadingOptions}>{loadingOptions && <option>Загрузка…</option>}<option value="all">Все кабинеты</option>{availableCabinets.map((cabinet) => <option key={cabinet.id} value={cabinet.id}>{cabinet.name}</option>)}</select></label>
        <fieldset><legend className="field-label mb-1.5">Маркетплейсы</legend><div className="flex flex-wrap gap-1.5">{marketplaceOptions.map(([value, label]) => <button key={value} type="button" onClick={() => toggleMarket(value)} className={`market-chip ${(draft.marketplaces ?? []).includes(value) ? "market-chip-active" : ""}`}>{label}</button>)}</div></fieldset>
        <label className="field-label">Сравнение<select value={draft.compare_from && draft.compare_to ? "custom" : "previous"} onChange={(event) => { if (event.target.value === "previous") { set("compare_from", undefined); set("compare_to", undefined); } }}><option value="previous">Предыдущий период</option><option value="custom" disabled>Произвольный период — через URL API</option></select><span className="mt-1 block text-[10px] font-normal normal-case tracking-normal text-[#858b84]">Сравнение рассчитывает backend.</span></label>
        {loadingOptions && <p className="flex items-center gap-1 text-[11px] text-[#858b84]"><Loader2 size={13} className="animate-spin" />Загружаем доступные области данных…</p>}
      </div>}
    </section>
  );
}
