import { cookies } from "next/headers";
import { NextResponse } from "next/server";
import { backendUrl } from "../cookies";

export async function POST() {
  const cookieStore = await cookies();
  const refreshToken = cookieStore.get("refresh_token")?.value;
  try {
    if (refreshToken) {
      await fetch(`${backendUrl()}/api/v1/auth/logout`, {
        method: "POST",
        headers: { cookie: `refresh_token=${refreshToken}`, accept: "application/json" },
        cache: "no-store",
      });
    }
  } catch {
    // Local cookies are still cleared below; a network failure must not keep a stale session in the browser.
  }
  cookieStore.delete("access_token");
  cookieStore.delete("refresh_token");
  return NextResponse.json({ ok: true });
}
