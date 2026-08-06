import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { DashboardView } from "@/components/dashboard/dashboard-view";
import { DataError } from "@/components/ui/data-state";
import { OperationalPage } from "@/components/operational-page";
import { ProductDetail } from "@/components/product-detail";
import { getOverview } from "@/utils/dashboard-data";
import { getOperationalPage } from "@/utils/operational-pages";
import { getProductDetail } from "@/utils/product-data";
import { isAuthenticationError } from "@/utils/api/client";
import { redirect } from "next/navigation";

export const dynamic = "force-dynamic";
type Props = { params: Promise<{ slug: string[] }>; searchParams: Promise<Record<string, string | string[] | undefined>> };
const titleMap: Record<string, string> = { dashboard: "Оцифровка", pulse: "Рука на пульсе", products: "Товары", advertising: "Реклама", "plan-fact": "План-факт", reports: "Отчёты", finance: "Финансы", management: "Управление" };
export async function generateMetadata({ params }: Props): Promise<Metadata> { const { slug } = await params; return { title: titleMap[slug[0]] ?? "Аналитика" }; }
function queryString(value: Record<string, string | string[] | undefined>) { const params = new URLSearchParams(); for (const [key, item] of Object.entries(value)) { if (typeof item === "string") params.set(key, item); else if (Array.isArray(item)) params.set(key, item.join(",")); } return params.toString(); }
function renderError(error: { message: string; requestId?: string; status?: number; code?: string }, path: string) {
  if (isAuthenticationError(error)) redirect(`/signin?next=${encodeURIComponent(path)}`);
  return <DataError message={error.message} requestId={error.requestId} status={error.status} code={error.code} />;
}

export default async function WorkspacePage({ params, searchParams }: Props) {
  const { slug } = await params;
  const query = queryString(await searchParams);
  const path = `/${slug.join("/")}`;
  if (path === "/dashboard") { const result = await getOverview(query); if (result.error) return renderError(result.error, path); return <DashboardView data={result.data!} />; }
  if (slug[0] === "products" && slug.length === 2 && !["unit-economics", "stocks"].includes(slug[1])) { const result = await getProductDetail(slug[1]); if (result.error) return renderError(result.error, path); return <ProductDetail product={result.data!} />; }
  const result = await getOperationalPage(path, query);
  if ("notFound" in result) return notFound();
  if (result.error) return renderError(result.error, path);
  return <OperationalPage data={result.data!} />;
}
