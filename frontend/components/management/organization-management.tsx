"use client";

import { FormEvent, useCallback, useEffect, useMemo, useState } from "react";
import { Building2, Check, Loader2, Pencil, Plus, RefreshCw, ShieldCheck, Trash2, X } from "lucide-react";
import { ApiError, apiRequest } from "@/utils/api/client";
import type { CabinetResponse, MemberResponse, OrganizationResponse, PageResult } from "@/utils/api/generated";

type OrganizationStats = { users: number; cabinets: number };

function errorMessage(error: unknown) {
  return error instanceof ApiError ? error.message : "Не удалось выполнить запрос";
}

export function OrganizationManagement() {
  const [organizations, setOrganizations] = useState<OrganizationResponse[]>([]);
  const [stats, setStats] = useState<Record<string, OrganizationStats>>({});
  const [name, setName] = useState("");
  const [editing, setEditing] = useState<string | null>(null);
  const [editingName, setEditingName] = useState("");
  const [loading, setLoading] = useState(true);
  const [pending, setPending] = useState<string | null>(null);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [organizationPage, cabinetPage] = await Promise.all([
        apiRequest<PageResult<OrganizationResponse>>("/api/v1/organizations?page=1&page_size=100"),
        apiRequest<PageResult<CabinetResponse>>("/api/v1/cabinets?page=1&page_size=100").catch(() => ({ items: [], total: 0, page: 1, page_size: 100, total_pages: 0, has_next: false, has_previous: false, next_page: null, previous_page: null })),
      ]);
      const nextStats: Record<string, OrganizationStats> = {};
      await Promise.all(organizationPage.items.map(async (organization) => {
        const members = await apiRequest<PageResult<MemberResponse>>(`/api/v1/organizations/${organization.id}/members?page=1&page_size=100`).catch(() => null);
        nextStats[organization.id] = {
          users: members?.total ?? 0,
          cabinets: cabinetPage.items.filter((cabinet) => cabinet.organization_id === organization.id).length,
        };
      }));
      setOrganizations(organizationPage.items);
      setStats(nextStats);
      setError("");
    } catch (value) {
      setError(errorMessage(value));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { void load(); }, [load]);

  const create = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setPending("create"); setError(""); setNotice("");
    try {
      await apiRequest<OrganizationResponse>("/api/v1/organizations", { method: "POST", body: { name: name.trim() } });
      setName(""); setNotice("Организация создана. Вы назначены её владельцем."); await load();
    } catch (value) { setError(errorMessage(value)); } finally { setPending(null); }
  };

  const update = async (id: string, values: { name?: string; is_active?: boolean }) => {
    setPending(id); setError(""); setNotice("");
    try {
      await apiRequest<OrganizationResponse>(`/api/v1/organizations/${id}`, { method: "PATCH", body: values });
      setEditing(null); setNotice("Изменения сохранены."); await load();
    } catch (value) { setError(errorMessage(value)); } finally { setPending(null); }
  };

  const deactivate = async (organization: OrganizationResponse) => {
    if (!window.confirm(`Деактивировать организацию «${organization.name}»? Доступ её участников будет закрыт.`)) return;
    setPending(organization.id); setError(""); setNotice("");
    try {
      await apiRequest(`/api/v1/organizations/${organization.id}`, { method: "DELETE" });
      setNotice("Организация деактивирована."); await load();
    } catch (value) { setError(errorMessage(value)); } finally { setPending(null); }
  };

  const activeCount = useMemo(() => organizations.filter((organization) => organization.is_active).length, [organizations]);

  return <div className="space-y-4">
    <section className="panel p-5">
      <div className="flex items-center gap-2"><Building2 size={18} className="text-[#34745f]" /><h2 className="section-title">Новая организация</h2></div>
      <p className="mt-2 text-xs leading-5 text-[#747a73]">После создания вы автоматически становитесь владельцем и получаете рабочий контекст организации.</p>
      <form className="mt-4 flex flex-col gap-3 sm:flex-row sm:items-end" onSubmit={create}>
        <label className="block flex-1 text-xs font-medium" htmlFor="new-organization-name">Название<input id="new-organization-name" className="form-input mt-1.5 w-full" value={name} onChange={(event) => setName(event.target.value)} minLength={2} maxLength={160} required placeholder="ООО «Мой бренд»" /></label>
        <button className="primary-button h-10 sm:min-w-48" disabled={pending === "create"}>{pending === "create" ? <Loader2 size={15} className="animate-spin" /> : <Plus size={15} />}Создать</button>
      </form>
    </section>

    {notice && <p className="flex items-center gap-2 rounded-md border border-[#cde1d8] bg-[#f4faf7] p-3 text-xs text-[#2b5f4d]" role="status"><Check size={16} />{notice}</p>}
    {error && <p className="rounded-md border border-[#edcfc7] bg-[#fff3f0] p-3 text-xs text-[#a54b31]" role="alert">{error}</p>}

    <section className="panel overflow-hidden">
      <div className="flex items-center justify-between border-b border-[#e5e7e2] px-4 py-3"><div><h2 className="section-title">Организации</h2><p className="mt-1 text-[11px] text-[#858b84]">Активных: {activeCount} из {organizations.length}</p></div><button className="secondary-button" onClick={() => void load()} disabled={loading}><RefreshCw size={14} className={loading ? "animate-spin" : ""} />Обновить</button></div>
      <div className="table-scroll"><table className="data-table"><thead><tr><th>Название</th><th>Владелец</th><th>Пользователи</th><th>Кабинеты</th><th>Статус</th><th><span className="sr-only">Действия</span></th></tr></thead><tbody>{organizations.length ? organizations.map((organization) => <tr key={organization.id}>
        <td>{editing === organization.id ? <input className="form-input h-8 min-w-48" value={editingName} onChange={(event) => setEditingName(event.target.value)} aria-label="Название организации" /> : <span className="font-medium">{organization.name}</span>}</td>
        <td className="font-mono text-[10px]">ID {organization.owner_user_id}</td>
        <td>{stats[organization.id]?.users ?? "—"}</td><td>{stats[organization.id]?.cabinets ?? "—"}</td>
        <td><span className={`status-badge ${organization.is_active ? "status-активен" : "status-критично"}`}>{organization.is_active ? "активна" : "деактивирована"}</span></td>
        <td><div className="flex justify-end gap-1">{editing === organization.id ? <><button className="icon-button" onClick={() => void update(organization.id, { name: editingName.trim() })} disabled={pending === organization.id} aria-label="Сохранить название"><Check size={15} /></button><button className="icon-button" onClick={() => setEditing(null)} aria-label="Отменить редактирование"><X size={15} /></button></> : <button className="icon-button" onClick={() => { setEditing(organization.id); setEditingName(organization.name); }} aria-label={`Изменить ${organization.name}`}><Pencil size={15} /></button>}{organization.is_active ? <button className="icon-button text-[#a85a2f]" onClick={() => void deactivate(organization)} disabled={pending === organization.id} aria-label={`Деактивировать ${organization.name}`}><Trash2 size={15} /></button> : <button className="icon-button text-[#34745f]" onClick={() => void update(organization.id, { is_active: true })} disabled={pending === organization.id} aria-label={`Активировать ${organization.name}`}><ShieldCheck size={15} /></button>}</div></td>
      </tr>) : <tr><td colSpan={6} className="py-12 text-center text-[#858b84]">{loading ? "Загружаем организации…" : "Организаций пока нет"}</td></tr>}</tbody></table></div>
    </section>
  </div>;
}
