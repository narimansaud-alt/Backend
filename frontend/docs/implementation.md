# Интеграция кабинета с Backend API

Frontend использует Next.js App Router и не содержит локального источника бизнес-данных. Все показатели, списки, права, статусы синхронизации и экспорт приходят из Backend API, описанного в `C:\Users\user\Desktop\Backend\api-docs.md`.

## API-слой

- `utils/api/generated.ts` — DTO backend: JWT auth, `PageResult`, organizations, cabinets, products, analytics, finance, sync, observability и exports.
- `utils/api/client.ts` — typed fetch-клиент с Bearer access token, refresh, timeout, AbortController, единым разбором `{ error, status, request_id, timestamp }` и обработкой 401/403.
- `utils/api/server.ts` — server-side forwarding cookie и access token из Next auth proxy.
- `utils/api/view-models.ts` — UI-модели, отделённые от backend DTO.
- `utils/api/query.ts` — выбор доступной организации и перевод URL-фильтров в `AnalyticsFilters`/`FinanceFilters`.

## Auth flow

1. `/signin` отправляет `username/password` в same-origin `/api/auth/login`.
2. Next proxy передаёт form-urlencoded запрос в `/api/v1/auth/login`, сохраняет access token и refresh token в HttpOnly cookies.
3. Browser API-запросы используют access token в памяти и Bearer header.
4. При 401 вызывается `/api/auth/refresh`, который обращается к `/api/v1/auth/refresh`, ротирует refresh-cookie и повторяет исходный запрос один раз.
5. `middleware.ts` защищает рабочие маршруты: если access token отсутствует или истёк, он один раз ротирует пару через refresh cookie до рендера страницы.
6. Server Components читают access token из cookie и передают его в backend.

## URL-фильтры

UI хранит период и выбранные кабинеты в URL. Adapter переводит их в backend-формат:

- `organization_ids` → обязательный `organization_id`;
- `date_from/date_to` → период;
- `compare_from/compare_to` → `compare_date_from/compare_date_to`;
- повторяющиеся `cabinet_ids` → `set[UUID]` query-параметры.

Backend не поддерживает frontend-only dimensions `brand_ids`, `category_ids`, `product_ids` и `product_group_ids` в текущем API, поэтому они не отправляются как невалидные параметры.

## Маршруты

`/dashboard` объединяет `/analytics/overview` и `/analytics/timeseries`. Остальные страницы используют фактические endpoints:

- каталог: `/products`, `/products/{id}`, `/product-groups`;
- analytics: `/analytics/products`, `/analytics/unit-economics`, `/analytics/advertising`, `/analytics/stocks`, `/analytics/plan-fact`;
- finance: `/finance/profit-loss`, `/finance/cash-flow`, `/finance/transactions`, `/expenses`, `/tax-rates`;
- management: `/organizations/{id}/members`, `/cabinets`, `/sync/overview`;
- export: `POST /exports` → polling `GET /exports/{id}`;
- observability: `POST /observability/client-errors` с обязательным `organization_id`.

Если backend не вернул поле, frontend показывает empty/partial state и не подставляет demo-значения.

## Проверка

```bash
pnpm typecheck
pnpm test
pnpm build
```

Для запуска нужны `API_URL`, `NEXT_PUBLIC_API_URL` и backend с включённым `/api/v1`.
