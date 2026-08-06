"use client";

import { FormEvent, useCallback, useEffect, useState } from "react";
import { Check, Clipboard, Loader2, Mail, RefreshCw, Save, UserPlus, UserX } from "lucide-react";
import { ApiError, apiRequest } from "@/utils/api/client";
import type { CabinetResponse, InvitationResponse, MemberResponse, OrganizationResponse, OrganizationRole, PageResult } from "@/utils/api/generated";

const roleLabels: Record<OrganizationRole, string> = {
  owner: "Владелец",
  admin: "Администратор",
  manager: "Менеджер",
  viewer: "Наблюдатель",
};

function message(error: unknown) {
  return error instanceof ApiError ? error.message : "Не удалось выполнить запрос";
}

export function TeamManagement() {
  const [organizations, setOrganizations] = useState<OrganizationResponse[]>([]);
  const [organizationId, setOrganizationId] = useState("");
  const [members, setMembers] = useState<MemberResponse[]>([]);
  const [cabinets, setCabinets] = useState<CabinetResponse[]>([]);
  const [drafts, setDrafts] = useState<Record<string, { role: OrganizationRole; cabinet_ids: string[] }>>({});
  const [pending, setPending] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [inviteLink, setInviteLink] = useState("");
  const [copied, setCopied] = useState(false);

  const loadMembers = useCallback(async (id: string) => {
    if (!id) return;
    setLoading(true);
    try {
      const result = await apiRequest<PageResult<MemberResponse>>(`/api/v1/organizations/${id}/members?page=1&page_size=100`);
      setMembers(result.items);
      setDrafts(Object.fromEntries(result.items.map((member) => [member.id, { role: member.role, cabinet_ids: member.cabinet_ids }])));
      setError("");
    } catch (value) {
      setError(message(value));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    Promise.all([
      apiRequest<PageResult<OrganizationResponse>>("/api/v1/organizations?page=1&page_size=100"),
      apiRequest<PageResult<CabinetResponse>>("/api/v1/cabinets?page=1&page_size=100").catch(() => ({ items: [], total: 0, page: 1, page_size: 100, total_pages: 0, has_next: false, has_previous: false, next_page: null, previous_page: null })),
    ]).then(([result, cabinetPage]) => {
        setCabinets(cabinetPage.items);
        setOrganizations(result.items);
        const first = result.items[0]?.id ?? "";
        setOrganizationId(first);
        if (first) return loadMembers(first);
        setLoading(false);
      })
      .catch((value) => { setError(message(value)); setLoading(false); });
  }, [loadMembers]);

  const invite = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setPending(true); setError(""); setInviteLink(""); setCopied(false);
    const form = new FormData(event.currentTarget);
    try {
      const result = await apiRequest<InvitationResponse>(`/api/v1/organizations/${organizationId}/invitations`, {
        method: "POST",
        body: { email: String(form.get("email") ?? ""), role: String(form.get("role") ?? "viewer"), expires_in_hours: 72 },
      });
      if (!result.invite_token) throw new ApiError("Backend не вернул токен приглашения", 500, "INVITE_TOKEN_MISSING");
      setInviteLink(`${window.location.origin}/invite?token=${encodeURIComponent(result.invite_token)}`);
      event.currentTarget.reset();
    } catch (value) {
      setError(message(value));
    } finally {
      setPending(false);
    }
  };

  const updateMember = async (member: MemberResponse) => {
    const draft = drafts[member.id];
    if (!draft) return;
    setPending(true); setError("");
    try {
      await apiRequest<MemberResponse>(`/api/v1/organizations/${organizationId}/members/${member.id}`, { method: "PATCH", body: draft });
      await loadMembers(organizationId);
    } catch (value) { setError(message(value)); } finally { setPending(false); }
  };

  const removeMember = async (member: MemberResponse) => {
    if (!window.confirm(`Отключить доступ пользователя ${member.email ?? member.username ?? member.user_id}?`)) return;
    setPending(true); setError("");
    try { await apiRequest(`/api/v1/organizations/${organizationId}/members/${member.id}`, { method: "DELETE" }); await loadMembers(organizationId); }
    catch (value) { setError(message(value)); } finally { setPending(false); }
  };

  const copy = async () => {
    await navigator.clipboard.writeText(inviteLink);
    setCopied(true);
  };

  return <div className="grid gap-4 xl:grid-cols-[380px_1fr]">
    <section className="panel h-fit p-5">
      <div className="flex items-center gap-2"><UserPlus size={18} className="text-[#34745f]" /><h2 className="section-title">Пригласить пользователя</h2></div>
      <p className="mt-2 text-xs leading-5 text-[#747a73]">Ссылка одноразовая, действует 72 часа. Новый пользователь задаст пароль сам.</p>
      <form className="mt-5 space-y-4" onSubmit={invite}>
        <label className="block text-xs font-medium">Организация<select className="form-input mt-1.5 w-full" value={organizationId} onChange={(event) => { setOrganizationId(event.target.value); void loadMembers(event.target.value); }} required>{organizations.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}</select></label>
        <label className="block text-xs font-medium">Email<input className="form-input mt-1.5 w-full" name="email" type="email" autoComplete="off" required placeholder="user@company.ru" /></label>
        <label className="block text-xs font-medium">Роль<select className="form-input mt-1.5 w-full" name="role" defaultValue="viewer">{(["admin", "manager", "viewer"] as OrganizationRole[]).map((role) => <option key={role} value={role}>{roleLabels[role]}</option>)}</select></label>
        <button className="primary-button w-full" disabled={pending || !organizationId}>{pending ? <Loader2 size={15} className="animate-spin" /> : <Mail size={15} />}Создать приглашение</button>
      </form>
      {inviteLink && <div className="mt-4 rounded-md border border-[#cde1d8] bg-[#f4faf7] p-3"><p className="text-xs font-medium text-[#2b5f4d]">Ссылка создана</p><p className="mt-2 break-all font-mono text-[10px] text-[#4f6a60]">{inviteLink}</p><button className="secondary-button mt-3" onClick={copy}>{copied ? <Check size={14} /> : <Clipboard size={14} />}{copied ? "Скопировано" : "Копировать"}</button></div>}
      {error && <p className="mt-4 rounded-md border border-[#edcfc7] bg-[#fff3f0] p-3 text-xs text-[#a54b31]">{error}</p>}
    </section>
    <section className="panel overflow-hidden">
      <div className="flex items-center justify-between border-b border-[#e5e7e2] px-4 py-3"><div><h2 className="section-title">Участники</h2><p className="mt-1 text-[11px] text-[#858b84]">Роль определяет доступ к финансам, кабинетам и команде.</p></div><button className="secondary-button" onClick={() => void loadMembers(organizationId)} disabled={loading}><RefreshCw size={14} className={loading ? "animate-spin" : ""} />Обновить</button></div>
      <div className="table-scroll"><table className="data-table"><thead><tr><th>Пользователь</th><th>Email</th><th>Роль</th><th>Кабинеты</th><th>Статус</th><th><span className="sr-only">Действия</span></th></tr></thead><tbody>{members.length ? members.map((member) => { const draft = drafts[member.id] ?? { role: member.role, cabinet_ids: member.cabinet_ids }; return <tr key={member.id}><td>{member.username ?? `ID ${member.user_id}`}</td><td>{member.email ?? "—"}</td><td><select className="form-input h-8 min-w-32 text-xs" value={draft.role} disabled={member.role === "owner" || pending} onChange={(event) => setDrafts((current) => ({ ...current, [member.id]: { ...draft, role: event.target.value as OrganizationRole } }))}>{(["owner", "admin", "manager", "viewer"] as OrganizationRole[]).map((role) => <option key={role} value={role}>{roleLabels[role]}</option>)}</select></td><td><select className="form-input h-8 min-w-40 text-xs" multiple size={Math.min(3, Math.max(1, cabinets.length))} value={draft.cabinet_ids} disabled={member.role === "owner" || pending} aria-label={`Кабинеты для ${member.username ?? member.user_id}`} onChange={(event) => setDrafts((current) => ({ ...current, [member.id]: { ...draft, cabinet_ids: Array.from(event.target.selectedOptions, (option) => option.value) } }))}>{cabinets.filter((cabinet) => cabinet.organization_id === organizationId).map((cabinet) => <option key={cabinet.id} value={cabinet.id}>{cabinet.name}</option>)}</select></td><td><span className={`status-badge ${member.is_active ? "status-активен" : "status-критично"}`}>{member.is_active ? "активен" : "отключён"}</span></td><td><div className="flex justify-end gap-1">{member.role !== "owner" && <><button className="icon-button text-[#34745f]" onClick={() => void updateMember(member)} disabled={pending} aria-label={`Сохранить ${member.username ?? member.user_id}`}><Save size={14} /></button><button className="icon-button text-[#a85a2f]" onClick={() => void removeMember(member)} disabled={pending} aria-label={`Отключить ${member.username ?? member.user_id}`}><UserX size={14} /></button></>}</div></td></tr>; }) : <tr><td colSpan={6} className="py-12 text-center text-[#858b84]">{loading ? "Загружаем участников…" : "Участников пока нет"}</td></tr>}</tbody></table></div>
    </section>
  </div>;
}
