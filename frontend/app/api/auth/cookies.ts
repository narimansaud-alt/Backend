import type { ResponseCookies } from "next/dist/compiled/@edge-runtime/cookies";

export function setCookieFromBackend(cookieStore: ResponseCookies, header: string | null, name: string, options: { httpOnly: boolean; secure: boolean; sameSite: "strict"; path: string; maxAge?: number }) {
  if (!header) return;
  const match = header.match(new RegExp(`${name}=([^;]+)`));
  if (match?.[1]) cookieStore.set(name, match[1], options);
}

export function backendUrl() {
  const value = process.env.API_URL;
  if (!value) throw new Error("API_URL is not configured");
  return value.replace(/\/$/, "");
}

