"use client";

import { Play, Plus, UserPlus } from "lucide-react";
import { useEffect, useState } from "react";
import { apiRequest } from "@/utils/api/client";
import type { CabinetResponse, PageResult, SyncKind, SyncStartResponse } from "@/utils/api/generated";

const syncKinds: SyncKind[] = ["catalog", "orders", "sales_returns", "finance_transactions", "advertising", "stocks", "analytics_funnel", "recompute_daily_analytics"];
export function RouteAction({ path, cabinetId }: { path: string; cabinetId?: string }) {
  const [state, setState] = useState<"idle" | "pending" | "done" | "error">("idle");
  const [cabinets, setCabinets] = useState<CabinetResponse[]>([]);
  const [selectedCabinetId, setSelectedCabinetId] = useState(cabinetId ?? "");
  const sync = path === "/management/sync"; const team = path === "/management/team";
  useEffect(() => {
    if (!sync || cabinetId) return;
    void apiRequest<PageResult<CabinetResponse>>("/api/v1/cabinets?page=1&page_size=100")
      .then((page) => { setCabinets(page.items); setSelectedCabinetId((current) => current || page.items[0]?.id || ""); })
      .catch(() => setCabinets([]));
  }, [cabinetId, sync]);
  const label = sync ? (state === "pending" ? "Запускаем…" : state === "done" ? "Задание создано" : state === "error" ? "Повторить" : "Запустить синхронизацию") : team ? "Пригласить" : "Добавить";
  const run = async () => {
    const activeCabinetId = cabinetId ?? selectedCabinetId;
    if (!sync || !activeCabinetId) return;
    setState("pending");
    try { const today = new Date().toISOString().slice(0, 10); await apiRequest<SyncStartResponse>(`/api/v1/cabinets/${activeCabinetId}/sync`, { method: "POST", body: { kinds: syncKinds, date_from: today, date_to: today } }); setState("done"); } catch { setState("error"); }
  };
  const Icon = sync ? Play : team ? UserPlus : Plus;
  return <div className="flex flex-wrap items-center gap-2">{sync && !cabinetId && <select className="form-input h-9 min-w-48 text-xs" aria-label="Кабинет для синхронизации" value={selectedCabinetId} onChange={(event) => setSelectedCabinetId(event.target.value)} disabled={!cabinets.length || state === "pending"}><option value="">Выберите кабинет</option>{cabinets.map((cabinet) => <option key={cabinet.id} value={cabinet.id}>{cabinet.name}</option>)}</select>}<button className="primary-button" onClick={run} disabled={!sync || !(cabinetId ?? selectedCabinetId) || state === "pending"} title={!sync || !(cabinetId ?? selectedCabinetId) ? "Backend требует выбрать конкретный кабинет" : undefined}><Icon size={15} />{label}</button></div>;
}
