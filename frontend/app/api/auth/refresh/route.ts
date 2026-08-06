import { cookies } from "next/headers";
import { NextResponse } from "next/server";
import { backendUrl, setCookieFromBackend } from "../cookies";

export async function POST() {
  try {
    const cookieStore = await cookies();
    const refreshToken = cookieStore.get("refresh_token")?.value;
    if (!refreshToken) return NextResponse.json({ error: { code: "NO_REFRESH_TOKEN", message: "Сессия истекла" } }, { status: 401 });
    const backendResponse = await fetch(`${backendUrl()}/api/v1/auth/refresh`, { method: "POST", headers: { cookie: `refresh_token=${refreshToken}`, accept: "application/json" }, cache: "no-store" });
    const payload = await backendResponse.json().catch(() => ({}));
    if (!backendResponse.ok) return NextResponse.json(payload, { status: backendResponse.status });
    const secure = process.env.NODE_ENV === "production";
    cookieStore.set("access_token", payload.access_token, { httpOnly: true, secure, sameSite: "strict", path: "/", maxAge: 900 });
    setCookieFromBackend(cookieStore, backendResponse.headers.get("set-cookie"), "refresh_token", { httpOnly: true, secure, sameSite: "strict", path: "/" });
    return NextResponse.json({ access_token: payload.access_token });
  } catch { return NextResponse.json({ error: { code: "AUTH_PROXY_ERROR", message: "Не удалось обновить сессию" } }, { status: 503 }); }
}

