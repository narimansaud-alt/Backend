"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { RefreshCw, Search, ShieldCheck, UserRound } from "lucide-react";
import { ApiError, apiRequest } from "@/utils/api/client";
import type { PageResult, UserAdminResponse } from "@/utils/api/generated";

function errorMessage(error: unknown) { return error instanceof ApiError ? error.message : "Не удалось загрузить пользователей"; }

export function UserManagement() {
  const [users, setUsers] = useState<UserAdminResponse[]>([]);
  const [query, setQuery] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const result = await apiRequest<PageResult<UserAdminResponse>>("/api/v1/users/?page=1&page_size=100&sort=created_at:desc");
      setUsers(result.items); setError("");
    } catch (value) { setError(errorMessage(value)); } finally { setLoading(false); }
  }, []);
  useEffect(() => { void load(); }, [load]);

  const filtered = useMemo(() => {
    const needle = query.trim().toLocaleLowerCase("ru");
    return users.filter((user) => !needle || `${user.username} ${user.email} ${user.roles.map((role) => role.name).join(" ")}`.toLocaleLowerCase("ru").includes(needle));
  }, [query, users]);

  return <section className="panel overflow-hidden">
    <div className="flex flex-wrap items-center justify-between gap-3 border-b border-[#e5e7e2] px-4 py-3"><div><h2 className="section-title">Пользователи</h2><p className="mt-1 text-[11px] text-[#858b84]">Данные и статусы загружаются из защищённого backend endpoint.</p></div><button className="secondary-button" onClick={() => void load()} disabled={loading}><RefreshCw size={14} className={loading ? "animate-spin" : ""} />Обновить</button></div>
    <div className="border-b border-[#e5e7e2] p-3"><label className="relative block max-w-sm"><Search className="pointer-events-none absolute left-2.5 top-1/2 -translate-y-1/2 text-[#929790]" size={14} /><input className="form-input h-9 w-full pl-8 text-xs" value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Поиск по имени, email или роли" aria-label="Поиск пользователей" /></label></div>
    {error ? <div className="p-6 text-center"><UserRound className="mx-auto text-[#a85a2f]" /><p className="mt-3 text-sm font-medium">Не удалось получить список пользователей</p><p className="mt-1 text-xs text-[#747a73]">{error}</p><button className="secondary-button mt-4" onClick={() => void load()}>Повторить</button></div> : <div className="table-scroll"><table className="data-table"><thead><tr><th>Пользователь</th><th>Email</th><th>Роли</th><th>Статус</th><th>Проверка</th></tr></thead><tbody>{filtered.length ? filtered.map((user) => <tr key={user.id}><td><span className="font-medium">{user.username}</span><span className="ml-2 font-mono text-[10px] text-[#929790]">#{user.id}</span></td><td>{user.email}</td><td>{user.roles.map((role) => role.name).join(", ") || "—"}</td><td><span className={`status-badge ${user.is_active ? "status-активен" : "status-критично"}`}>{user.is_active ? "активен" : "заблокирован"}</span></td><td>{user.is_verified ? <span className="inline-flex items-center gap-1 text-[10px] text-[#34745f]"><ShieldCheck size={13} />подтверждён</span> : <span className="text-[10px] text-[#a85a2f]">не подтверждён</span>}</td></tr>) : <tr><td colSpan={5} className="py-12 text-center text-[#858b84]">{loading ? "Загружаем пользователей…" : "Пользователи не найдены"}</td></tr>}</tbody></table></div>}
    <div className="border-t border-[#e5e7e2] px-4 py-2.5 text-[11px] text-[#858b84]">Показано {filtered.length} из {users.length}</div>
  </section>;
}
