import { NextRequest, NextResponse } from "next/server";
import { backendUrl } from "../../auth/cookies";

export const dynamic = "force-dynamic";

type RouteContext = { params: Promise<{ path: string[] }> };

async function proxy(request: NextRequest, context: RouteContext) {
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
    });

    const responseHeaders = new Headers();
    for (const name of ["content-type", "content-disposition", "x-request-id", "cache-control"]) {
      const value = response.headers.get(name);
      if (value) responseHeaders.set(name, value);
    }
    return new NextResponse(response.body, { status: response.status, headers: responseHeaders });
  } catch {
    return NextResponse.json(
      { error: { code: "BACKEND_PROXY_ERROR", message: "Не удалось связаться с backend. Проверьте API_URL на frontend." } },
      { status: 503 },
    );
  }
}

export const GET = proxy;
export const POST = proxy;
export const PUT = proxy;
export const PATCH = proxy;
export const DELETE = proxy;
