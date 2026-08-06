import type { Decimal, Marketplace, OrganizationRole, SyncStatus } from "./generated";

export type CellFormat = "text" | "money" | "percent" | "number" | "status";
export type DataStatus = "fresh" | "stale" | "partial" | "unknown";

export interface MetricViewModel {
  id: string;
  label: string;
  value: string;
  previous: string;
  absolute_delta?: string;
  relative_delta?: string;
  unit: "rub" | "percent" | "count";
  change_direction: "higher_is_better" | "lower_is_better";
  status: DataStatus;
}

export interface DashboardViewModel {
  updated_at?: string;
  status: DataStatus;
  metrics: MetricViewModel[];
  timeseries: Array<{ date: string; sales: string; profit: string; orders: number }>;
  marketplaces: Array<{ marketplace: Marketplace; sales: string; profit: string; share: number }>;
  warnings: Array<{ code: string; message: string; action_label?: string; action_href?: string }>;
  expense_structure: Array<{ label: string; value: string; share: number; color?: string }>;
  product_rows: Array<{ id: string; name: string; sku: string; marketplace: Marketplace; sales: string; orders: number; profit: string; margin: string; stock_days: number }>;
  waterfall: Array<{ label: string; value: string; share: number; kind: "income" | "expense" | "result" }>;
}

export interface OperationalViewModel {
  path: string;
  title: string;
  description: string;
  endpoint: string;
  updated_at?: string;
  status: DataStatus;
  metrics: Array<{ label: string; value: string; previous?: string; delta?: string; format: Exclude<CellFormat, "status"> }>;
  columns: Array<{ key: string; label: string; format: CellFormat }>;
  rows: Array<Record<string, string | number | null>>;
  warnings: Array<{ code: string; message: string; action_label?: string; action_href?: string }>;
  empty_message?: string;
}

export interface ProductDetailViewModel {
  id: string;
  name: string;
  sku: string;
  marketplace?: Marketplace;
  organization_id: string;
  group_id?: string | null;
  brand?: string | null;
  category?: string | null;
}

export interface SessionViewModel {
  user?: { id: number; username: string; email: string };
  organization_name?: string;
  role?: OrganizationRole;
}

export interface SyncRow {
  status: SyncStatus;
  value: number;
}

export function decimalToString(value: Decimal | undefined): string {
  return value === null || value === undefined ? "" : String(value);
}
