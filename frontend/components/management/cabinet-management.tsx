"use client";

import { FormEvent, useCallback, useEffect, useMemo, useState } from "react";
import { CheckCircle2, KeyRound, Loader2, Plus, RefreshCw, ShieldCheck } from "lucide-react";
import { ApiError, apiRequest } from "@/utils/api/client";
import type { CabinetResponse, Marketplace, OrganizationResponse, PageResult } from "@/utils/api/generated";
import { OrganizationCreate } from "./organization-create";

const marketplaceLabels: Record<Marketplace, string> = { wildberries: "Wildberries", ozon: "Ozon", yandex_market: "Яндекс Маркет" };

function message(error: unknown) { return error instanceof ApiError ? error.message : "Не удалось выполнить запрос"; }

function credential(form: FormData, marketplace: Marketplace, prefix = "") {
  if (marketplace === "ozon") return JSON.stringify({ client_id: String(form.get(`${prefix}client_id`) ?? "").trim(), api_key: String(form.get(`${prefix}api_key`) ?? "").trim() });
  return String(form.get(`${prefix}token`) ?? "").trim();
}

function CredentialFields({ marketplace, prefix = "" }: { marketplace: Marketplace; prefix?: string }) {
  if (marketplace === "ozon") return <div className="grid gap-3 sm:grid-cols-2"><label className="block text-xs font-medium">Client ID<input className="form-input mt-1.5 w-full" name={`${prefix}client_id`} autoComplete="off" required /></label><label className="block text-xs font-medium">API key<input className="form-input mt-1.5 w-full" name={`${prefix}api_key`} type="password" autoComplete="new-password" required /></label></div>;
  return <label className="block text-xs font-medium">{marketplace === "wildberries" ? "API token" : "API key"}<textarea className="form-input mt-1.5 min-h-24 w-full resize-y" name={`${prefix}token`} autoComplete="off" required /></label>;
}

export function CabinetManagement() {
  const [organizations, setOrganizations] = useState<OrganizationResponse[]>([]);
  const [cabinets, setCabinets] = useState<CabinetResponse[]>([]);
  const [marketplace, setMarketplace] = useState<Marketplace>("wildberries");
  const [rotateCabinetId, setRotateCabinetId] = useState("");
  const [pending, setPending] = useState<"create" | "rotate" | string | null>(null);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [organizationsLoaded, setOrganizationsLoaded] = useState(false);
  const rotateCabinet = useMemo(() => cabinets.find((item) => item.id === rotateCabinetId), [cabinets, rotateCabinetId]);

  const load = useCallback(async () => {
    try {
      const [orgs, items] = await Promise.all([
        apiRequest<PageResult<OrganizationResponse>>("/api/v1/organizations?page=1&page_size=100"),
        apiRequest<PageResult<CabinetResponse>>("/api/v1/cabinets?page=1&page_size=100"),
      ]);
      setOrganizations(orgs.items); setCabinets(items.items); setOrganizationsLoaded(true);
      setRotateCabinetId((current) => current || items.items[0]?.id || ""); setError("");
    } catch (value) { setError(message(value)); }
  }, []);

  useEffect(() => { void load(); }, [load]);

  const create = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault(); setPending("create"); setError(""); setNotice("");
    const form = new FormData(event.currentTarget);
    try {
      await apiRequest<CabinetResponse>("/api/v1/cabinets", { method: "POST", body: { organization_id: String(form.get("organization_id")), marketplace, external_id: String(form.get("external_id") ?? "").trim(), name: String(form.get("name") ?? "").trim(), credential: credential(form, marketplace) } });
      setNotice("Кабинет подключён, ключ проверен и сохранён в зашифрованном виде."); event.currentTarget.reset(); await load();
    } catch (value) { setError(message(value)); } finally { setPending(null); }
  };

  const rotate = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault(); if (!rotateCabinet) return; setPending("rotate"); setError(""); setNotice("");
    const form = new FormData(event.currentTarget);
    try {
      await apiRequest(`/api/v1/cabinets/${rotateCabinet.id}/credentials/validate`, { method: "POST", body: { credential: credential(form, rotateCabinet.marketplace, "rotate_") } });
      setNotice("Новый ключ проверен и сохранён."); event.currentTarget.reset(); await load();
    } catch (value) { setError(message(value)); } finally { setPending(null); }
  };

  const validateStored = async (id: string) => {
    setPending(id); setError(""); setNotice("");
    try { await apiRequest(`/api/v1/cabinets/${id}/credentials/validate`, { method: "POST", body: {} }); setNotice("Сохранённый ключ действителен."); await load(); }
    catch (value) { setError(message(value)); } finally { setPending(null); }
  };

  return <div className="space-y-4">
    {organizationsLoaded && !organizations.length && <OrganizationCreate />}
    <div className="grid gap-4 xl:grid-cols-2">
      <section className="panel p-5"><div className="flex items-center gap-2"><Plus size={18} className="text-[#34745f]" /><h2 className="section-title">Подключить кабинет</h2></div><p className="mt-2 text-xs leading-5 text-[#747a73]">Backend сначала проверяет ключ в API маркетплейса и только затем шифрует его AES-GCM.</p><form className="mt-5 space-y-4" onSubmit={create}><label className="block text-xs font-medium">Организация<select className="form-input mt-1.5 w-full" name="organization_id" required>{organizations.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}</select></label><label className="block text-xs font-medium">Маркетплейс<select className="form-input mt-1.5 w-full" value={marketplace} onChange={(event) => setMarketplace(event.target.value as Marketplace)}>{Object.entries(marketplaceLabels).map(([value, label]) => <option key={value} value={value}>{label}</option>)}</select></label><div className="grid gap-3 sm:grid-cols-2"><label className="block text-xs font-medium">Название<input className="form-input mt-1.5 w-full" name="name" required placeholder="Основной кабинет" /></label><label className="block text-xs font-medium">{marketplace === "yandex_market" ? "Business ID" : marketplace === "ozon" ? "Seller ID" : "ID продавца"}<input className="form-input mt-1.5 w-full" name="external_id" required /></label></div><CredentialFields marketplace={marketplace} /><button className="primary-button w-full" disabled={pending === "create" || !organizations.length}>{pending === "create" ? <Loader2 size={15} className="animate-spin" /> : <ShieldCheck size={15} />}Проверить и подключить</button></form></section>
      <section className="panel p-5"><div className="flex items-center gap-2"><KeyRound size={18} className="text-[#34745f]" /><h2 className="section-title">Обновить ключ</h2></div><p className="mt-2 text-xs leading-5 text-[#747a73]">Старый секрет не показывается. Новый заменит его только после успешной проверки.</p><form className="mt-5 space-y-4" onSubmit={rotate}><label className="block text-xs font-medium">Кабинет<select className="form-input mt-1.5 w-full" value={rotateCabinetId} onChange={(event) => setRotateCabinetId(event.target.value)} required>{cabinets.map((item) => <option key={item.id} value={item.id}>{marketplaceLabels[item.marketplace]} · {item.name}</option>)}</select></label>{rotateCabinet && <CredentialFields marketplace={rotateCabinet.marketplace} prefix="rotate_" />}<button className="primary-button w-full" disabled={pending === "rotate" || !rotateCabinet}>{pending === "rotate" ? <Loader2 size={15} className="animate-spin" /> : <KeyRound size={15} />}Проверить и сохранить</button></form></section>
    </div>
    {notice && <p className="flex items-center gap-2 rounded-md border border-[#cde1d8] bg-[#f4faf7] p-3 text-xs text-[#2b5f4d]"><CheckCircle2 size={16} />{notice}</p>}{error && <p className="rounded-md border border-[#edcfc7] bg-[#fff3f0] p-3 text-xs text-[#a54b31]">{error}</p>}
    <section className="panel overflow-hidden"><div className="border-b border-[#e5e7e2] px-4 py-3"><h2 className="section-title">Подключённые кабинеты</h2></div><div className="table-scroll"><table className="data-table"><thead><tr><th>Кабинет</th><th>Маркетплейс</th><th>Ключ</th><th>Scopes</th><th>Проверка</th></tr></thead><tbody>{cabinets.length ? cabinets.map((item) => <tr key={item.id}><td>{item.name}</td><td>{marketplaceLabels[item.marketplace]}</td><td className="font-mono text-[11px]">{item.credential_masked_hint ?? "—"}</td><td>{item.credential_scopes.join(", ") || "—"}</td><td><button className="secondary-button" onClick={() => void validateStored(item.id)} disabled={pending === item.id}>{pending === item.id ? <Loader2 size={14} className="animate-spin" /> : <RefreshCw size={14} />}Проверить</button></td></tr>) : <tr><td colSpan={5} className="py-12 text-center text-[#858b84]">Кабинеты ещё не подключены</td></tr>}</tbody></table></div></section>
  </div>;
}
