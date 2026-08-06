/**
 * Backend OpenAPI contract.
 *
 * Keep view models in `view-models.ts`; this file mirrors the REST DTOs from
 * the backend app schemas and core pagination DTO.
 */
export type Decimal = string | number | null;
export type UUID = string;
export type Marketplace = "wildberries" | "ozon" | "yandex_market";
export type OrganizationRole = "owner" | "admin" | "manager" | "viewer";
export type SyncKind = "catalog" | "orders" | "sales_returns" | "finance_transactions" | "advertising" | "stocks" | "analytics_funnel" | "recompute_daily_analytics";
export type SyncStatus = "queued" | "running" | "retry_wait" | "paused" | "succeeded" | "failed" | "cancelled";

export interface PageResult<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
  has_next: boolean;
  has_previous: boolean;
  next_page: number | null;
  previous_page: number | null;
}

export interface ApiErrorResponse {
  error: { code: string; message: string; detail?: unknown };
  status: number;
  request_id: UUID;
  timestamp: number;
}

export interface AccessTokenResponse { access_token: string; }
export interface UserResponse { id: number; username: string; email: string; }
export interface OrganizationResponse { id: UUID; name: string; owner_user_id: number; is_active: boolean; }
export interface MemberResponse { id: UUID; organization_id: UUID; user_id: number; role: OrganizationRole; is_active: boolean; }
export interface InvitationResponse { id: UUID; email: string; role: OrganizationRole; status: string; expires_at: string; invite_token?: string | null; }

export interface CabinetResponse {
  id: UUID;
  organization_id: UUID;
  marketplace: Marketplace;
  external_id: string;
  name: string;
  currency: string;
  timezone: string;
  is_active: boolean;
  credential_masked_hint?: string | null;
  credential_scopes: string[];
  credential_validated_at?: string | null;
}
export interface CredentialValidationResponse { masked_hint: string; scopes: string[]; validated_at: string; }
export interface SyncStartResponse { job_ids: UUID[]; }
export interface SyncJobResponse {
  id: UUID; organization_id: UUID; cabinet_id: UUID; parent_job_id?: UUID | null; kind: SyncKind;
  period_from: string; period_to: string; status: SyncStatus; stage: string; attempts: number;
  progress: Decimal; error_code?: string | null; error_message?: string | null; repeated_error_count: number;
  rows_processed: number; started_at?: string | null; finished_at?: string | null; next_retry_at?: string | null;
}
export interface SyncOverviewResponse { queued: number; running: number; retry_wait: number; paused: number; failed: number; last_success_at?: string | null; }

export interface ProductResponse { id: UUID; organization_id: UUID; group_id?: UUID | null; internal_sku: string; name: string; brand?: string | null; category?: string | null; }
export interface ProductGroupResponse { id: UUID; organization_id: UUID; name: string; }

export interface AnalyticsFiltersDto { organization_id: UUID; date_from: string; date_to: string; cabinet_ids: UUID[]; compare_date_from?: string | null; compare_date_to?: string | null; }
export interface PeriodResponse { date_from: string; date_to: string; }
export interface MetricResponse { code: string; value: Decimal; unit: string; previous_value: Decimal; delta: Decimal; delta_percent: Decimal; status: string; }
export interface FreshnessResponse { cabinet_id: UUID; last_success_at?: string | null; complete_through?: string | null; missing_kinds: string[]; }
export interface AnalyticsOverviewResponse { period: PeriodResponse; compare_period: PeriodResponse; metrics: MetricResponse[]; data_freshness: FreshnessResponse[]; warnings: string[]; }
export interface TimeSeriesMetric { code: string; value: Decimal; }
export interface TimeSeriesPoint { business_date: string; metrics: TimeSeriesMetric[]; }
export interface TimeSeriesResponse { period: PeriodResponse; points: TimeSeriesPoint[]; warnings: string[]; }

export interface ExpenseResponse { id: UUID; organization_id: UUID; cabinet_id?: UUID | null; category_id: UUID; business_date: string; amount: Decimal; description?: string | null; }
export interface TaxRateResponse { id: UUID; valid_from: string; valid_to?: string | null; rate_percent: Decimal; base_metric: string; }
export interface PlanResponse { id: UUID; organization_id: UUID; name: string; period_from: string; period_to: string; }
export interface ProfitLossLine { code: string; value: Decimal; }
export interface ProfitLossResponse { period_from: string; period_to: string; lines: ProfitLossLine[]; warnings: string[]; }
export interface CashFlowResponse { inflow: Decimal; outflow: Decimal; net_cash_flow: Decimal; }
export interface FinanceTransactionResponse { id: UUID; cabinet_id: UUID; marketplace: string; external_key: string; operation_type: string; business_date: string; amount: Decimal; }

export interface ClientErrorRequest { organization_id: UUID; timestamp: string; route: string; release?: string; browser?: string | null; message: string; stack?: string | null; component_stack?: string | null; request_id?: string | null; }
export interface ClientErrorResponse { id: UUID; fingerprint: string; occurrences: number; last_seen_at: string; }
export interface ExportJobResponse { id: UUID; organization_id: UUID; status: "queued" | "running" | "succeeded" | "failed"; format: "csv" | "xlsx"; storage_key?: string | null; error_code?: string | null; created_at: string; updated_at: string; download_url?: string | null; }
