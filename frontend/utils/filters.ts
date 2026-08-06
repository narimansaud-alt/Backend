import type { AnalyticsFiltersDto, Marketplace } from "./api/generated";

export type FilterState = {
  date_from?: string;
  date_to?: string;
  compare_from?: string;
  compare_to?: string;
  organization_ids?: string[];
  marketplaces?: Marketplace[];
  cabinet_ids?: string[];
  brand_ids?: string[];
  category_ids?: string[];
  product_ids?: string[];
  product_group_ids?: string[];
};

export function moscowDate(offsetDays = 0) {
  const today = new Date(new Intl.DateTimeFormat("en-CA", { timeZone: "Europe/Moscow" }).format(new Date()));
  today.setUTCDate(today.getUTCDate() + offsetDays);
  return today.toISOString().slice(0, 10);
}

export function defaultDateRange(): Pick<FilterState, "date_from" | "date_to"> {
  return { date_from: moscowDate(-29), date_to: moscowDate() };
}

const arrayKeys = ["organization_ids", "marketplaces", "cabinet_ids", "brand_ids", "category_ids", "product_ids", "product_group_ids"] as const;
const dateKeys = ["date_from", "date_to", "compare_from", "compare_to"] as const;

export function parseFilters(input: URLSearchParams | Record<string, string | string[] | undefined>): FilterState {
  const getValues = (key: string) => input instanceof URLSearchParams
    ? input.getAll(key).flatMap((value) => value.split(",")).filter(Boolean)
    : (Array.isArray(input[key]) ? input[key] : input[key] ? input[key].split(",") : []).filter(Boolean) as string[];
  const state: FilterState = {};
  for (const key of dateKeys) { const value = getValues(key)[0]; if (value) state[key] = value; }
  for (const key of arrayKeys) { const values = getValues(key); if (values.length) (state as Record<string, unknown>)[key] = values; }
  return state;
}

export function serializeFilters(filters: FilterState) {
  const params = new URLSearchParams();
  for (const [key, value] of Object.entries(filters)) {
    if (Array.isArray(value)) value.filter(Boolean).forEach((item) => params.append(key, item));
    else if (typeof value === "string" && value) params.set(key, value);
  }
  return params;
}

export function activeFilterCount(filters: FilterState) {
  return Object.entries(filters).filter(([key, value]) => !key.startsWith("date_") && !key.startsWith("compare_") && (Array.isArray(value) ? value.length : Boolean(value))).length;
}

export function toBackendAnalyticsFilters(filters: FilterState, organizationId: string): AnalyticsFiltersDto {
  if (!filters.date_from || !filters.date_to) throw new Error("Для запроса backend нужны date_from и date_to");
  return {
    organization_id: organizationId,
    date_from: filters.date_from,
    date_to: filters.date_to,
    cabinet_ids: filters.cabinet_ids ?? [],
    compare_date_from: filters.compare_from ?? null,
    compare_date_to: filters.compare_to ?? null,
  };
}

export function backendFiltersQuery(filters: AnalyticsFiltersDto) {
  const params = new URLSearchParams({ organization_id: filters.organization_id, date_from: filters.date_from, date_to: filters.date_to });
  filters.cabinet_ids.forEach((cabinetId) => params.append("cabinet_ids", cabinetId));
  if (filters.compare_date_from) params.set("compare_date_from", filters.compare_date_from);
  if (filters.compare_date_to) params.set("compare_date_to", filters.compare_date_to);
  return params.toString();
}

export type Role = "owner" | "admin" | "manager" | "viewer";
export type Permission = "finance:manage" | "plan:manage" | "team:manage" | "cabinet:manage" | "export:read";

const grants: Record<Role, Permission[]> = {
  owner: ["finance:manage", "plan:manage", "team:manage", "cabinet:manage", "export:read"],
  admin: ["finance:manage", "plan:manage", "team:manage", "cabinet:manage", "export:read"],
  manager: ["plan:manage", "export:read"],
  viewer: ["export:read"],
};

export function can(role: Role, permission: Permission) { return grants[role].includes(permission); }
