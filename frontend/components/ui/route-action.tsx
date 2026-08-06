"use client";

import { Play, Plus, UserPlus } from "lucide-react";
import { useState } from "react";
import { apiRequest } from "@/utils/api/client";
import type { SyncKind, SyncStartResponse } from "@/utils/api/generated";

const syncKinds: SyncKind[] = ["catalog", "orders", "sales_returns", "finance_transactions", "advertising", "stocks", "analytics_funnel", "recompute_daily_analytics"];
export function RouteAction({ path, cabinetId }: { path: string; cabinetId?: string }) {
  const [state, setState] = useState<"idle" | "pending" | "done" | "error">("idle");
  const sync = path === "/management/sync"; const team = path === "/management/team";
  const label = sync ? (state === "pending" ? "Запускаем…" : state === "done" ? "Задание создано" : state === "error" ? "Повторить" : "Запустить синхронизацию") : team ? "Пригласить" : "Добавить";
  const run = async () => {
    if (!sync || !cabinetId) return;
    setState("pending");
    try { const today = new Date().toISOString().slice(0, 10); await apiRequest<SyncStartResponse>(`/api/v1/cabinets/${cabinetId}/sync`, { method: "POST", body: { kinds: syncKinds, date_from: today, date_to: today } }); setState("done"); } catch { setState("error"); }
  };
  const Icon = sync ? Play : team ? UserPlus : Plus;
  return <button className="primary-button" onClick={run} disabled={!sync || !cabinetId || state === "pending"} title={!sync || !cabinetId ? "Backend требует выбрать конкретный кабинет" : undefined}><Icon size={15} />{label}</button>;
}
