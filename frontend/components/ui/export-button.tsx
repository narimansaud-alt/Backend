"use client";

import { Download, Loader2 } from "lucide-react";
import { useState } from "react";
import { apiRequest } from "@/utils/api/client";
import type { ExportJobResponse, OrganizationResponse, PageResult } from "@/utils/api/generated";

function moscowDate(offsetDays = 0) { const value = new Date(new Intl.DateTimeFormat("en-CA", { timeZone: "Europe/Moscow" }).format(new Date())); value.setUTCDate(value.getUTCDate() + offsetDays); return value.toISOString().slice(0, 10); }
const wait = (ms: number) => new Promise((resolve) => window.setTimeout(resolve, ms));

export function ExportButton({ filename = "report.csv" }: { filename?: string }) {
  const [status, setStatus] = useState<ExportJobResponse["status"] | "idle">("idle");
  const run = async () => {
    setStatus("queued");
    try {
      const search = new URLSearchParams(window.location.search);
      let organizationId = search.get("organization_id") ?? search.get("organization_ids");
      if (!organizationId) organizationId = (await apiRequest<PageResult<OrganizationResponse>>("/api/v1/organizations?page=1&page_size=1")).items[0]?.id;
      if (!organizationId) throw new Error("ORGANIZATION_REQUIRED");
      const filters = { organization_id: organizationId, date_from: search.get("date_from") ?? moscowDate(-29), date_to: search.get("date_to") ?? moscowDate(), cabinet_ids: search.getAll("cabinet_ids"), compare_date_from: search.get("compare_from"), compare_date_to: search.get("compare_to") };
      let job = await apiRequest<ExportJobResponse>("/api/v1/exports", { method: "POST", body: { format: "csv", filters } });
      for (let attempt = 0; attempt < 12 && (job.status === "queued" || job.status === "running"); attempt += 1) { setStatus(job.status); await wait(1500); job = await apiRequest<ExportJobResponse>(`/api/v1/exports/${job.id}`); }
      setStatus(job.status);
      if (job.download_url) { const anchor = document.createElement("a"); anchor.href = job.download_url; anchor.download = filename; anchor.rel = "noreferrer"; anchor.click(); }
    } catch { setStatus("failed"); }
  };
  return <button className="secondary-button" onClick={run} disabled={status === "queued" || status === "running"} aria-live="polite">{status === "queued" || status === "running" ? <Loader2 size={15} className="animate-spin" /> : <Download size={15} />}{status === "queued" || status === "running" ? "Готовим экспорт…" : status === "succeeded" ? "Экспорт готов" : status === "failed" ? "Повторить экспорт" : "Экспорт"}</button>;
}
