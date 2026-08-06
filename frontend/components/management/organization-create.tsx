"use client";

import { Building2, CheckCircle2, Loader2 } from "lucide-react";
import { FormEvent, useState } from "react";
import { useRouter } from "next/navigation";
import { ApiError, apiRequest } from "@/utils/api/client";
import type { OrganizationResponse } from "@/utils/api/generated";

function errorMessage(error: unknown) {
  return error instanceof ApiError ? error.message : "Не удалось создать организацию";
}

export function OrganizationCreate() {
  const router = useRouter();
  const [pending, setPending] = useState(false);
  const [error, setError] = useState("");

  const create = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setPending(true);
    setError("");
    const form = new FormData(event.currentTarget);
    try {
      await apiRequest<OrganizationResponse>("/api/v1/organizations", {
        method: "POST",
        body: { name: String(form.get("name") ?? "").trim() },
      });
      router.replace("/dashboard");
      router.refresh();
    } catch (value) {
      setError(errorMessage(value));
    } finally {
      setPending(false);
    }
  };

  return <section className="mx-auto max-w-2xl rounded-xl border border-[#dfe2dc] bg-white p-6 shadow-sm md:p-8">
    <div className="flex size-12 items-center justify-center rounded-lg bg-[#eaf5ef] text-[#34745f]"><Building2 size={23} /></div>
    <p className="mt-5 text-xs font-semibold uppercase tracking-[.14em] text-[#34745f]">Первичная настройка</p>
    <h2 className="mt-2 text-2xl font-semibold text-[#20231f]">Создайте рабочую организацию</h2>
    <p className="mt-2 max-w-xl text-sm leading-6 text-[#747a73]">Организация нужна, чтобы хранить кабинеты маркетплейсов, команду и аналитику в одном рабочем контуре.</p>
    <form className="mt-6 flex flex-col gap-3 sm:flex-row sm:items-end" onSubmit={create}>
      <label className="block flex-1 text-xs font-medium" htmlFor="organization-name">Название организации<input id="organization-name" name="name" className="form-input mt-1.5 w-full" minLength={2} maxLength={160} required placeholder="Например, ООО «Мой бренд»" /></label>
      <button className="primary-button h-10 sm:min-w-48" disabled={pending}>{pending && <Loader2 size={15} className="animate-spin" />}{pending ? "Создаём…" : "Создать организацию"}</button>
    </form>
    {error && <p className="mt-4 rounded-md border border-[#edcfc7] bg-[#fff3f0] p-3 text-xs text-[#a54b31]" role="alert">{error}</p>}
    <p className="mt-5 flex items-center gap-2 text-[11px] text-[#858b84]"><CheckCircle2 size={14} className="text-[#34745f]" />После создания появится возможность подключить Wildberries, Ozon и Яндекс Маркет.</p>
  </section>;
}
