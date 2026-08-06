import { ApiError } from "./client";
import { serverApiRequest } from "./server";
import type { OrganizationResponse, PageResult } from "./generated";
import { backendFiltersQuery, defaultDateRange, parseFilters, toBackendAnalyticsFilters, type FilterState } from "../filters";

export async function resolveOrganizationId(filters: FilterState) {
  const selected = filters.organization_ids?.[0];
  if (selected) return selected;
  const organizations = await serverApiRequest<PageResult<OrganizationResponse>>("/api/v1/organizations?page=1&page_size=1");
  const first = organizations.items[0];
  if (!first) throw new ApiError("Backend не вернул доступную организацию.", 422, "ORGANIZATION_REQUIRED");
  return first.id;
}

export async function analyticsQuery(queryString: string) {
  const filters = { ...defaultDateRange(), ...parseFilters(new URLSearchParams(queryString)) };
  const organizationId = await resolveOrganizationId(filters);
  return backendFiltersQuery(toBackendAnalyticsFilters(filters, organizationId));
}

export async function financeQuery(queryString: string) {
  const filters = { ...defaultDateRange(), ...parseFilters(new URLSearchParams(queryString)) };
  const organizationId = await resolveOrganizationId(filters);
  if (!filters.date_from || !filters.date_to) throw new ApiError("Для финансового отчёта нужны даты периода.", 422, "PERIOD_REQUIRED");
  const params = new URLSearchParams({ organization_id: organizationId, date_from: filters.date_from, date_to: filters.date_to });
  (filters.cabinet_ids ?? []).forEach((cabinetId) => params.append("cabinet_ids", cabinetId));
  return params.toString();
}

export function selectedOrganizationId(queryString: string) {
  return parseFilters(new URLSearchParams(queryString)).organization_ids?.[0];
}
