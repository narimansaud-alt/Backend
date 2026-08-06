"use client";

import { FormEvent, useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { CheckCircle2, Loader2, UserPlus } from "lucide-react";
import { ApiError, apiRequest } from "@/utils/api/client";
import type { InvitationRegistrationResponse, MemberResponse } from "@/utils/api/generated";

function message(error: unknown) { return error instanceof ApiError ? error.message : "Не удалось принять приглашение"; }

export default function InvitePage() {
  const router = useRouter();
  const [token, setToken] = useState("");
  const [pending, setPending] = useState<"register" | "accept" | null>(null);
  const [error, setError] = useState("");
  const [done, setDone] = useState(false);
  useEffect(() => { setToken(new URLSearchParams(window.location.search).get("token") ?? ""); }, []);

  const register = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault(); setPending("register"); setError("");
    const form = new FormData(event.currentTarget);
    try {
      await apiRequest<InvitationRegistrationResponse>("/api/v1/organizations/invitations/register", { method: "POST", body: { token, username: String(form.get("username") ?? ""), password: String(form.get("password") ?? ""), password_repeat: String(form.get("password_repeat") ?? "") } });
      setDone(true);
    } catch (value) { setError(message(value)); } finally { setPending(null); }
  };

  const acceptExisting = async () => {
    setPending("accept"); setError("");
    try { await apiRequest<MemberResponse>("/api/v1/organizations/invitations/accept", { method: "POST", body: { token } }); router.replace("/dashboard"); }
    catch (value) { setError(message(value)); } finally { setPending(null); }
  };

  if (done) return <main className="grid min-h-screen place-items-center p-5"><div className="panel w-full max-w-md p-7 text-center"><CheckCircle2 className="mx-auto text-[#34745f]" size={36} /><h1 className="mt-4 text-xl font-semibold">Учётная запись создана</h1><p className="mt-2 text-sm text-[#747a73]">Теперь войдите с указанным username или email.</p><Link className="primary-button mt-6" href="/signin">Перейти ко входу</Link></div></main>;

  return <main className="grid min-h-screen place-items-center p-5"><div className="panel w-full max-w-md p-7"><div className="flex items-center gap-2"><UserPlus size={21} className="text-[#34745f]" /><h1 className="text-xl font-semibold">Принять приглашение</h1></div><p className="mt-2 text-sm leading-6 text-[#747a73]">Создайте учётную запись. Email и роль уже зафиксированы в одноразовом приглашении.</p>{!token && <p className="mt-4 rounded-md border border-[#edcfc7] bg-[#fff3f0] p-3 text-xs text-[#a54b31]">В ссылке отсутствует токен приглашения.</p>}<form className="mt-6 space-y-4" onSubmit={register}><label className="block text-xs font-medium">Username<input className="form-input mt-1.5 w-full" name="username" minLength={3} maxLength={64} required autoComplete="username" /></label><label className="block text-xs font-medium">Пароль<input className="form-input mt-1.5 w-full" name="password" type="password" minLength={8} required autoComplete="new-password" /></label><label className="block text-xs font-medium">Повторите пароль<input className="form-input mt-1.5 w-full" name="password_repeat" type="password" minLength={8} required autoComplete="new-password" /></label><p className="text-[11px] leading-5 text-[#858b84]">Нужны заглавная и строчная буквы, цифра и специальный символ.</p><button className="primary-button w-full" disabled={!token || pending !== null}>{pending === "register" && <Loader2 size={15} className="animate-spin" />}Создать аккаунт</button></form><div className="my-5 flex items-center gap-3 text-[10px] uppercase tracking-wider text-[#9ba09a]"><span className="h-px flex-1 bg-[#e2e5e0]" />или<span className="h-px flex-1 bg-[#e2e5e0]" /></div><button className="secondary-button w-full" onClick={() => void acceptExisting()} disabled={!token || pending !== null}>{pending === "accept" && <Loader2 size={15} className="animate-spin" />}У меня уже есть аккаунт</button>{error && <p className="mt-4 rounded-md border border-[#edcfc7] bg-[#fff3f0] p-3 text-xs text-[#a54b31]">{error}</p>}</div></main>;
}
