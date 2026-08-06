"use client";

import { FormEvent, useState } from "react";
import Link from "next/link";
import { ArrowLeft, Loader2 } from "lucide-react";
import { apiRequest, ApiError } from "@/utils/api/client";

export default function ResetPassword() {
  const [message, setMessage] = useState(""); const [error, setError] = useState(""); const [pending, setPending] = useState(false);
  const submit = async (event: FormEvent<HTMLFormElement>) => { event.preventDefault(); setMessage(""); setError(""); setPending(true); const email = new FormData(event.currentTarget).get("email"); try { await apiRequest("/api/v1/auth/password-resets", { method: "POST", body: { email } }); setMessage("Если адрес зарегистрирован, инструкция отправлена."); } catch (value) { setError(value instanceof ApiError ? value.message : "Не удалось отправить запрос"); } finally { setPending(false); } };
  return <main className="grid min-h-screen place-items-center bg-[#f4f5f3] p-5"><form onSubmit={submit} className="w-full max-w-sm rounded-lg border border-[#dfe2dc] bg-white p-7 shadow-sm"><Link href="/signin" className="inline-flex items-center gap-1 text-xs text-[#34745f] hover:underline"><ArrowLeft size={14} />Назад ко входу</Link><h1 className="mt-6 text-2xl font-semibold">Восстановление пароля</h1><p className="mt-2 text-sm text-[#6d726c]">Введите рабочий email. Backend проверит доступ и отправит инструкцию.</p><label className="mt-6 block text-sm font-medium" htmlFor="email">Email<input id="email" name="email" type="email" required className="form-input mt-2 w-full" placeholder="name@company.ru" /></label>{message && <p className="mt-4 rounded-md border border-[#cde1d8] bg-[#f4faf7] p-2.5 text-xs text-[#2b5f4d]" role="status">{message}</p>}{error && <p className="mt-4 rounded-md border border-[#edcfc7] bg-[#fff3f0] p-2.5 text-xs text-[#a54b31]" role="alert">{error}</p>}<button disabled={pending} className="primary-button mt-6 w-full">{pending && <Loader2 size={15} className="animate-spin" />}Отправить запрос</button></form></main>;
}
