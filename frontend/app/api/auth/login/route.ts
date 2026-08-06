import { cookies } from "next/headers";
import { NextResponse } from "next/server";
import { backendUrl, setCookieFromBackend } from "../cookies";

export async function POST(request: Request) {
  try {
    const body = await request.json() as { username?: string; password?: string };
    const form = new URLSearchParams({ username: body.username ?? "", password: body.password ?? "" });
    const backendResponse = await fetch(`${backendUrl()}/api/v1/auth/login`, { method: "POST", headers: { "content-type": "application/x-www-form-urlencoded", accept: "application/json" }, body: form, cache: "no-store" });
    const payload = await backendResponse.json().catch(() => ({}));
    if (!backendResponse.ok) return NextResponse.json(payload, { status: backendResponse.status });
    const cookieStore = await cookies();
    const secure = process.env.NODE_ENV === "production";
    cookieStore.set("access_token", payload.access_token, { httpOnly: true, secure, sameSite: "strict", path: "/", maxAge: 900 });
    setCookieFromBackend(cookieStore, backendResponse.headers.get("set-cookie"), "refresh_token", { httpOnly: true, secure, sameSite: "strict", path: "/" });
    return NextResponse.json({ access_token: payload.access_token });
  } catch { return NextResponse.json({ error: { code: "AUTH_PROXY_ERROR", message: "Не удалось выполнить вход" } }, { status: 503 }); }
}

