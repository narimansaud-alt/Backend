# REST API документация для frontend

Документ собирает API приложения (`FastAPI`) для использования в работе с frontend. Базовая схема построена на коде роутеров в `app/*/routes.py`.

## Базовые URL и окружения

- Базовый префикс API: ` /api/v1` (`app_config.API_V1_STR`).
- Коды API без префикса:
  - `GET /health` — простой healthcheck.
  - `GET /ready` — проверка готовности сервисов.
  - `GET /metrics` — метрики Prometheus.
- `GET /api/v1/openapi.json` доступен только в `ENVIRONMENT=local|testing`.

## Авторизация

Почти все бизнес-эндпоинты требуют JWT в `Authorization`:

- `Authorization: Bearer <access_token>`

Обновление access-токена выполняется через cookie `refresh_token` (HttpOnly, Secure, SameSite=`strict`, `path=/`) у метода `POST /api/v1/auth/refresh`.

Часть публичных маршрутов не требует авторизации:

- `/api/v1/auth/login`
- `/api/v1/auth/refresh` (только refresh-cookie)
- `/api/v1/auth/verifications/email`
- `/api/v1/auth/password-resets`
- `/api/v1/auth/oauth/{provider}/authorize`
- `/api/v1/auth/oauth/{provider}/callback`
- `/health`, `/ready`, `/metrics`
- `/api/v1/openapi.json` (сейчас только в local/testing)

`POST /api/v1/users/register` по умолчанию отключён, если `USER_REGISTRATION_ALLOWED = false` (по умолчанию `false` в `app/auth/config.py`).

## Универсальные структуры

- Формат ошибки (для всех неуспешных ответов в приложении):
  - `error: {code, message, detail}`
  - `status: int`
  - `request_id: UUID`
  - `timestamp: float`
- Пагинация (в ответах `PageResult`):
  - `items: []`
  - `total: number`
  - `page: number`
  - `page_size: number`
- Типы:
  - UUID — строка
  - Decimal — строка/число (сохраняется через JSON сериализацию модели)

## Коды ошибок, которые встречаются чаще всего

- `400` — ошибка валидации/бизнес-правила (например `WRONG_LOGIN_DATA`, `PASSWORD_MISMATCH`, `INVALID_TOKEN` и др.)
- `401` — `NOT_AUTHNTICATED`
- `403` — `ACCESS_DENIED`
- `404` — не найденный ресурс (`NOT_FOUND_*`)
- `409` — конфликт (`DUPLICATE_*`, `PROTECTED_PERMISSION`)
- `422` — ошибка валидации тела/параметров (валидатор FastAPI)
- `500` — ошибка сервера

> Полный перечень кодов ошибок зависит от бизнес-слоя: они определены через `ApplicationError` и оборачиваются в единую схему ошибки.

## Endpoints

Ниже перечислены все фактические REST-эндпоинты, присутствующие в текущей кодовой базе.

### 1) Core / Health

1. `GET /health`
   - Описание: быстрый статус API.
   - Auth: не требуется
   - 200: `"Ok"`

2. `GET /ready`
   - Описание: readiness-пробы для API/DB/Redis/worker-heartbeat.
   - Auth: не требуется
   - 200: `{"status":"ready", "checks":{...}}`
   - 503: если одна из проверок `unavailable`

3. `GET /metrics`
   - Описание: метрики Prometheus.
   - Auth: не требуется (по текущей конфигурации роутера)

### 2) Auth (`/api/v1/auth`)

#### 2.1 Вход/выход

1. `POST /api/v1/auth/login`
   - `Content-Type: application/x-www-form-urlencoded`
   - Тело: `OAuth2PasswordRequestForm` (`username`, `password`)
   - 200: `AccessTokenResponse` → `{ "access_token": "..." }`
   - 400: `WRONG_LOGIN_DATA`

2. `POST /api/v1/auth/refresh`
   - Refresh берётся из cookie `refresh_token`.
   - 200: `AccessTokenResponse`
   - 400: `INVALID_TOKEN` / `EXPIRED_TOKEN`
   - 404: `NOT_FOUND_OR_INACTIVE_SESSION`

3. `POST /api/v1/auth/logout`
   - Refresh token из cookie `refresh_token`
   - 204: успешный logout
   - 400: `INVALID_TOKEN`

#### 2.2 Email/Password recovery

4. `POST /api/v1/auth/verifications/email`
   - Body: `SendVerifyCodeRequest { email }`
   - 204
   - 404: `NOT_FOUND_USER`

5. `POST /api/v1/auth/password-resets`
   - Body: `SendResetPasswordCodeRequest { email }`
   - 204
   - 404: `NOT_FOUND_USER`

6. `POST /api/v1/auth/verifications/email/verify`
   - Body: `VerifyEmailRequest { token }`
   - 204
   - 400: `INVALID_TOKEN`
   - 404: `NOT_FOUND_USER`

7. `POST /api/v1/auth/password-resets/confirm`
   - Body: `ResetPasswordRequest { token, password, password_repeat }`
   - 204
   - 400: `INVALID_TOKEN`, `PASSWORD_MISMATCH`
   - 404: `NOT_FOUND_USER`

#### 2.3 OAuth

8. `GET /api/v1/auth/oauth/{provider}/authorize`
   - Описание: URL для авторизации поставщика OAuth (без пользователя)
   - 200: `OAuthUrlResponse { url }`
   - 400: `NOT_EXIST_PROVIDER_OAUTH`

9. `GET /api/v1/auth/oauth/{provider}/authorize/connect`
   - Требуется авторизация
   - 200: `OAuthUrlResponse { url }`
   - 400: `NOT_EXIST_PROVIDER_OAUTH`

10. `GET /api/v1/auth/oauth/{provider}/callback`
   - Query: `code`, `state`
   - Set-Cookie: `refresh_token`
   - 200: `AccessTokenResponse`
   - 400: `NOT_EXIST_PROVIDER_OAUTH`
   - 404: `OAUTH_STATE_NOT_FOUND`, `NOT_FOUND_USER`
   - 409: `LINKED_ANOTHER_USER_OAUTH`

### 3) Users (`/api/v1/users`)

> Все ниже перечисленные точки в коде защищены через `AuthCurrentUserJWTData`, кроме `/register`.

1. `POST /api/v1/users/register`
   - Body: `UserCreateRequest` (`username`, `email`, `password`, `password_repeat`)
   - 201: `UserResponse {id, username, email}`
   - 400: `PASSWORD_MISMATCH`
   - 409: `DUPLICATE_USER`

2. `GET /api/v1/users/me`
   - 200: `UserResponse`

3. `POST /api/v1/users/{user_id}/roles`
   - Body: `RoleAssignRequest { role_name }`
   - 200: пустой ответ

4. `DELETE /api/v1/users/{user_id}/roles/{role_name}`
   - 204

5. `POST /api/v1/users/{user_id}/permissions`
   - Body: `UserPermissionRequest { permissions: [\"...\"] }`
   - 200

6. `DELETE /api/v1/users/{user_id}/permissions`
   - Body: `UserPermissionRequest`
   - 204

7. `GET /api/v1/users`
   - Query: `GetUsersRequest`
   - 200: `PageResult<UserDTO>`

8. `GET /api/v1/users/sessions`
   - Query: не требует body
   - 200: `list[SessionDTO]`

### 4) Permissions (`/api/v1/permissions`)

1. `POST /api/v1/permissions`
   - Body: `PermissionCreateRequest { name }`
   - 201

2. `DELETE /api/v1/permissions/{name}`
   - 204

3. `GET /api/v1/permissions`
   - Query: `GetPermissionsRequest`
   - 200: `PageResult<PermissionDTO>`

### 5) Roles (`/api/v1/roles`)

1. `POST /api/v1/roles`
   - Body: `RoleCreateRequest { name, description, security_level, permissions }`
   - 201

2. `GET /api/v1/roles`
   - Query: `GetRolesRequest`
   - 200: `PageResult<RoleDTO>`

3. `POST /api/v1/roles/{role_name}/permissions`
   - Body: `RolePermissionRequest { permission: [..] }`
   - 200

4. `DELETE /api/v1/roles/{role_name}/permissions`
   - Body: `RolePermissionRequest`
   - 200

### 6) Sessions (`/api/v1/sessions`)

1. `DELETE /api/v1/sessions/{session_id}`
   - 204

2. `GET /api/v1/sessions`
   - Query: `GetSessionsRequest`
   - 200: `PageResult<SessionDTO>`

### 7) Organizations (`/api/v1/organizations`)

1. `GET /api/v1/organizations`
   - Query: `page`, `page_size`
   - 200: `PageResult<OrganizationResponse>`

2. `POST /api/v1/organizations`
   - Body: `OrganizationCreateRequest { name }`
   - 201: `OrganizationResponse`

3. `GET /api/v1/organizations/{organization_id}/members`
   - Query: `page`, `page_size`
   - 200: `PageResult<MemberResponse>`

4. `POST /api/v1/organizations/{organization_id}/invitations`
   - Body: `InvitationCreateRequest { email, role, expires_in_hours }`
   - 201: `InvitationResponse`

5. `POST /api/v1/organizations/invitations/accept`
   - Body: `InvitationAcceptRequest { token }`
   - 200: `MemberResponse`

6. `PATCH /api/v1/organizations/{organization_id}/members/{member_id}`
   - Body: `MemberUpdateRequest { role, cabinet_ids }`
   - 200: `MemberResponse`

7. `DELETE /api/v1/organizations/{organization_id}/members/{member_id}`
   - 204

### 8) Marketplaces и синк (`/api/v1`)

1. `GET /api/v1/cabinets`
   - Query: `page`, `page_size`, `marketplace`
   - 200: `PageResult<CabinetResponse>`

2. `POST /api/v1/cabinets`
   - Body: `CabinetCreateRequest { organization_id, marketplace, external_id, name, credential }`
   - 201: `CabinetResponse`

3. `GET /api/v1/cabinets/{cabinet_id}`
   - 200: `CabinetResponse`

4. `PATCH /api/v1/cabinets/{cabinet_id}`
   - Body: `CabinetUpdateRequest { name?, is_active? }`
   - 200: `CabinetResponse`

5. `DELETE /api/v1/cabinets/{cabinet_id}`
   - 204

6. `POST /api/v1/cabinets/{cabinet_id}/credentials/validate`
   - Body: `CredentialValidateRequest { credential? }`
   - 200: `CredentialValidationResponse`

7. `POST /api/v1/cabinets/{cabinet_id}/sync`
   - Body: `SyncStartRequest { kinds, date_from, date_to }`
   - 202: `SyncStartResponse { job_ids }`

8. `GET /api/v1/cabinets/{cabinet_id}/sync-jobs`
   - Query: `page`, `page_size`
   - 200: `PageResult<SyncJobResponse>`

9. `GET /api/v1/sync-jobs/{job_id}`
   - 200: `SyncJobResponse`

10. `POST /api/v1/sync-jobs/{job_id}/retry`
   - 200: `SyncJobResponse`

11. `GET /api/v1/sync/overview`
   - 200: `SyncOverviewResponse`

### 9) Catalog (`/api/v1`)

1. `GET /api/v1/products`
   - Query: `organization_id` + пагинация
   - 200: `PageResult<ProductResponse>`

2. `GET /api/v1/products/{product_id}`
   - 200: `ProductResponse`

3. `PATCH /api/v1/products/{product_id}`
   - Body: `ProductUpdateRequest { name?, group_id? }`
   - 200: `ProductResponse`

4. `POST /api/v1/products/costs/import`
   - Body: `ProductCostImportRequest { organization_id, rows[] }`
   - 200: `{"imported": number}`

5. `GET /api/v1/product-groups`
   - Query: `organization_id`
   - 200: `ProductGroupResponse[]`

6. `POST /api/v1/product-groups`
   - Body: `ProductGroupCreateRequest { organization_id, name }`
   - 201: `ProductGroupResponse`

7. `PATCH /api/v1/product-groups/{group_id}`
   - Body: `ProductGroupUpdateRequest { name }`
   - Query: `organization_id`
   - 200: `ProductGroupResponse`

8. `DELETE /api/v1/product-groups/{group_id}`
   - Query: `organization_id`
   - 204

### 10) Analytics (`/api/v1`)

Все точки аналитики (кроме ошибок и экспортов) используют параметры `AnalyticsFilters`.

1. `GET /api/v1/analytics/overview`
   - Query: `organization_id, date_from, date_to, cabinet_ids?, compare_date_from?, compare_date_to?`
   - 200: `AnalyticsOverviewResponse`

2. `GET /api/v1/analytics/timeseries`
   - Query: `AnalyticsFilters`
   - 200: `TimeSeriesResponse`

3. `GET /api/v1/analytics/products`
4. `GET /api/v1/analytics/unit-economics`
5. `GET /api/v1/analytics/advertising`
6. `GET /api/v1/analytics/stocks`
7. `GET /api/v1/analytics/plan-fact`
   - Query: `AnalyticsFilters`
   - 200: `TimeSeriesResponse`

8. `POST /api/v1/observability/client-errors`
   - Body: `ClientErrorRequest`
   - 201: `ClientErrorResponse`

9. `GET /api/v1/observability/client-errors`
   - Query: `organization_id`, `page`, `page_size`
   - 200: `PageResult<ClientErrorResponse>`

10. `POST /api/v1/exports`
   - Body: `ExportRequest { format: "csv" | "xlsx", filters: AnalyticsFilters }`
   - 202: `ExportJobResponse`

11. `GET /api/v1/exports/{export_id}`
   - 200: `ExportJobResponse`

### 11) Finance (`/api/v1`)

1. `GET /api/v1/expenses`
   - Query: `FinanceFilters`
   - 200: `ExpenseResponse[]`

2. `POST /api/v1/expenses`
   - Body: `ExpenseRequest`
   - 201: `ExpenseResponse`

3. `PATCH /api/v1/expenses/{expense_id}`
   - Body: `ExpenseRequest`
   - 200: `ExpenseResponse`

4. `DELETE /api/v1/expenses/{expense_id}`
   - Query: `organization_id`
   - 204

5. `GET /api/v1/tax-rates`
   - Query: `organization_id`
   - 200: `TaxRateResponse[]`

6. `PUT /api/v1/tax-rates`
   - Body: `TaxRatesRequest { organization_id, rates[] }`
   - 200: `TaxRateResponse[]`

7. `GET /api/v1/plans`
   - Query: `organization_id`
   - 200: `PlanResponse[]`

8. `POST /api/v1/plans`
   - Body: `PlanRequest`
   - 201: `PlanResponse`

9. `PATCH /api/v1/plans/{plan_id}`
   - Body: `PlanRequest`
   - 200: `PlanResponse`

10. `DELETE /api/v1/plans/{plan_id}`
   - Query: `organization_id`
   - 204

11. `GET /api/v1/finance/profit-loss`
   - Query: `FinanceFilters`
   - 200: `ProfitLossResponse`

12. `GET /api/v1/finance/cash-flow`
   - Query: `FinanceFilters`
   - 200: `CashFlowResponse`

13. `GET /api/v1/finance/transactions`
   - Query: `FinanceFilters`, `page`, `page_size`
   - 200: `PageResult<FinanceTransactionResponse>`

## Справочники и enum

- Marketplace (`Marketplace`): `wildberries`, `ozon`, `yandex_market`
- Роли в организациях (`OrganizationRole`): `owner`, `admin`, `manager`, `viewer`
- Статусы приглашений (`InvitationStatus`): `pending`, `accepted`, `revoked`, `expired`
- Типы синка (`SyncKind`):
  - `catalog`, `orders`, `sales_returns`, `finance_transactions`, `advertising`, `stocks`, `analytics_funnel`, `recompute_daily_analytics`
- Статусы синка (`SyncStatus`):
  - `queued`, `running`, `retry_wait`, `paused`, `succeeded`, `failed`, `cancelled`
- Формат экспорта: `csv`, `xlsx`
- Кодировки метрик / поля периода/ограничения: см. `docs/metric-dictionary.md`

## Примечания для фронта

1. Удаление ресурсов и ряд операций возвращают `204` с пустым телом.
2. Большинство list-эндпоинтов принимает явную пагинацию: `page` (по умолчанию `1`) и `page_size` (по умолчанию `20`, максимум `100`).
3. `login` использует form-data, не JSON.
4. Для отладки удобно запускать `GET /api/v1/openapi.json` в локальном/тестовом режиме и использовать его как контракт.
5. Права доступа (какие именно нужны для каждого endpoint) реализованы в auth-сервисах/политиках и через `AccessDeniedError` возвращаются как `403`.
