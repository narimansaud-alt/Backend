"use client";

import { useEffect } from "react";
import { sanitizeError } from "@/utils/error-sanitizer";
import { apiRequest } from "@/utils/api/client";
import type { OrganizationResponse, PageResult } from "@/utils/api/generated";

export function ClientErrorReporter() {
  useEffect(() => {
    const sent = new Map<string, number>();
    let reporting = false;
    const report = (value: unknown) => {
      if (reporting) return;
      const baseUrl = process.env.NEXT_PUBLIC_API_URL;
      if (!baseUrl) return;
      const payload = sanitizeError(value);
      const key = `${payload.message}:${window.location.pathname}`;
      const last = sent.get(key) ?? 0;
      if (Date.now() - last < 60_000) return;
      sent.set(key, Date.now());
      reporting = true;
      apiRequest<PageResult<OrganizationResponse>>("/api/v1/organizations?page=1&page_size=1").then((organizations) => {
        const organizationId = organizations.items[0]?.id;
        if (!organizationId) return;
        return apiRequest("/api/v1/observability/client-errors", {
          method: "POST",
          body: { organization_id: organizationId, timestamp: new Date().toISOString(), ...payload, route: window.location.pathname, release: process.env.NEXT_PUBLIC_RELEASE_ID ?? "local" },
        });
      }).catch(() => undefined).finally(() => { reporting = false; });
    };
    const onError = (event: ErrorEvent) => report(event.error ?? event.message);
    const onRejection = (event: PromiseRejectionEvent) => report(event.reason);
    window.addEventListener("error", onError);
    window.addEventListener("unhandledrejection", onRejection);
    return () => { window.removeEventListener("error", onError); window.removeEventListener("unhandledrejection", onRejection); };
  }, []);
  return null;
}
