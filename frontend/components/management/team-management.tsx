"use client";

import { FormEvent, useCallback, useEffect, useState } from "react";
import { Check, Clipboard, Loader2, Mail, RefreshCw, UserPlus } from "lucide-react";
import { ApiError, apiRequest } from "@/utils/api/client";
import type { InvitationResponse, MemberResponse, OrganizationResponse, OrganizationRole, PageResult } from "@/utils/api/generated";

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
      setError("");
    } catch (value) {
      setError(message(value));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    apiRequest<PageResult<OrganizationResponse>>("/api/v1/organizations?page=1&page_size=100")
      .then((result) => {
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
      <div className="table-scroll"><table className="data-table"><thead><tr><th>Пользователь</th><th>Email</th><th>Роль</th><th>Статус</th></tr></thead><tbody>{members.length ? members.map((member) => <tr key={member.id}><td>{member.username ?? `ID ${member.user_id}`}</td><td>{member.email ?? "—"}</td><td>{roleLabels[member.role]}</td><td><span className={`status-badge ${member.is_active ? "status-succeeded" : "status-failed"}`}>{member.is_active ? "активен" : "отключён"}</span></td></tr>) : <tr><td colSpan={4} className="py-12 text-center text-[#858b84]">{loading ? "Загружаем участников…" : "Участников пока нет"}</td></tr>}</tbody></table></div>
    </section>
  </div>;
}
