import { NextRequest, NextResponse } from "next/server";

const protectedPath = /^\/(dashboard|pulse|reports(?:\/|$)|products(?:\/|$)|advertising|plan-fact|finance(?:\/|$)|management(?:\/|$))/;

function isExpired(token: string | undefined) {
  if (!token) return true;
  try {
    const encodedPayload = token.split(".")[1];
    if (!encodedPayload) return true;
    const normalized = encodedPayload.replace(/-/g, "+").replace(/_/g, "/");
    const padded = normalized.padEnd(Math.ceil(normalized.length / 4) * 4, "=");
    const payload = JSON.parse(atob(padded)) as { exp?: number };
    return typeof payload.exp !== "number" || payload.exp <= Math.floor(Date.now() / 1000) + 5;
  } catch {
    return true;
  }
}

function cookieValue(header: string | null, name: string) {
  const match = header?.match(new RegExp(`(?:^|,\\s*)${name}=([^;]+)`));
  return match?.[1];
}

function signIn(request: NextRequest) {
  const next = `${request.nextUrl.pathname}${request.nextUrl.search}`;
  return NextResponse.redirect(new URL(`/signin?next=${encodeURIComponent(next)}`, request.url));
}

async function refreshSession(refreshToken: string) {
  const apiUrl = process.env.API_URL?.replace(/\/$/, "");
  if (!apiUrl) return null;

  const backendResponse = await fetch(`${apiUrl}/api/v1/auth/refresh`, {
    method: "POST",
    headers: { cookie: `refresh_token=${refreshToken}`, accept: "application/json" },
    cache: "no-store",
  });
  if (!backendResponse.ok) return null;

  const payload = await backendResponse.json().catch(() => ({})) as { access_token?: string };
  const rotatedRefreshToken = cookieValue(backendResponse.headers.get("set-cookie"), "refresh_token");
  if (!payload.access_token || !rotatedRefreshToken) return null;

  const response = NextResponse.next();
  const secure = process.env.NODE_ENV === "production";
  response.cookies.set("access_token", payload.access_token, { httpOnly: true, secure, sameSite: "strict", path: "/", maxAge: 900 });
  response.cookies.set("refresh_token", rotatedRefreshToken, { httpOnly: true, secure, sameSite: "strict", path: "/" });
  return response;
}

export async function middleware(request: NextRequest) {
  if (!protectedPath.test(request.nextUrl.pathname)) return NextResponse.next();

  const accessToken = request.cookies.get("access_token")?.value;
  const refreshToken = request.cookies.get("refresh_token")?.value;
  if (accessToken && !isExpired(accessToken)) return NextResponse.next();
  if (!refreshToken) return signIn(request);

  try {
    return (await refreshSession(refreshToken)) ?? signIn(request);
  } catch {
    return signIn(request);
  }
}

export const config = {
  matcher: [
    "/dashboard/:path*",
    "/pulse/:path*",
    "/reports/:path*",
    "/products/:path*",
    "/advertising/:path*",
    "/plan-fact/:path*",
    "/finance/:path*",
    "/management/:path*",
  ],
};
