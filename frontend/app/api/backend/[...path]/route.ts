import { NextRequest, NextResponse } from "next/server";
import { backendUrl } from "../../auth/cookies";

export const dynamic = "force-dynamic";

type RouteContext = { params: Promise<{ path: string[] }> };

async function proxy(request: NextRequest, context: RouteContext) {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 15_000);
  try {
    const { path } = await context.params;
    const target = `${backendUrl()}/${path.join("/")}${request.nextUrl.search}`;
    const headers = new Headers(request.headers);
    headers.delete("host");
    headers.delete("content-length");

    const body = request.method === "GET" || request.method === "HEAD" ? undefined : await request.arrayBuffer();
    const response = await fetch(target, {
      method: request.method,
      headers,
      body,
      cache: "no-store",
      signal: controller.signal,
    });

    const responseHeaders = new Headers();
    for (const name of ["content-type", "content-disposition", "x-request-id", "cache-control"]) {
      const value = response.headers.get(name);
      if (value) responseHeaders.set(name, value);
    }
    return new NextResponse(response.body, { status: response.status, headers: responseHeaders });
  } catch (error) {
    const timeout = error instanceof DOMException && error.name === "AbortError";
    return NextResponse.json(
      { error: { code: timeout ? "BACKEND_TIMEOUT" : "BACKEND_PROXY_ERROR", message: timeout ? "Backend не ответил вовремя. Повторите запрос." : "Не удалось связаться с backend. Проверьте API_URL на frontend." } },
      { status: timeout ? 504 : 503 },
    );
  } finally { clearTimeout(timeout); }
}

export const GET = proxy;
export const POST = proxy;
export const PUT = proxy;
export const PATCH = proxy;
export const DELETE = proxy;
