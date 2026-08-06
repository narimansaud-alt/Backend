import { headers } from "next/headers";
import { redirect } from "next/navigation";
import { apiRequest, ApiError } from "./client";

export async function serverApiRequest<T>(path: string, options: Parameters<typeof apiRequest>[1] = {}) {
  const incoming = await headers();
  const cookie = incoming.get("cookie");
  const authorization = incoming.get("authorization");
  const accessToken = cookie?.match(/(?:^|;\s*)access_token=([^;]+)/)?.[1];
  try {
    return await apiRequest<T>(path, {
      ...options,
      headers: { ...options.headers, ...(cookie ? { cookie } : {}), ...(authorization ? { authorization } : accessToken ? { authorization: `Bearer ${decodeURIComponent(accessToken)}` } : {}) },
    });
  } catch (error) {
    if (error instanceof ApiError && error.status === 401) redirect("/signin");
    throw error;
  }
}
