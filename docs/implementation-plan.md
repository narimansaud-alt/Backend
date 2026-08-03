# Repository audit and implementation map

## Existing architecture

The repository is a layered modular monolith. `app/auth` is the reference
module: routes map request schemas to commands/queries, the mediator resolves a
handler from Dishka, handlers enforce RBAC and call repositories, and the async
session owns the transaction. ORM metadata is assembled in
`app/core/models.py`; Alembic imports that metadata. Taskiq and the scheduler
share the application container.

## File map

- `app/organizations`: organization/member/invitation models, scope gateway,
  policies, repositories, commands/queries, provider, and routes.
- `app/marketplaces`: cabinets, encrypted credentials, sync job/checkpoint/event
  models, connector port/adapters, retry and period-window logic, tasks,
  provider, and routes.
- `app/catalog`: products, offers, groups, cost history, filters, repository,
  command/query handlers, provider, and routes.
- `app/analytics`: fact/projection/custom-metric/client-error/export models,
  formulas and safe DSL, report queries, recomputation/export tasks, provider,
  and routes.
- `app/finance`: expense/tax/cash-flow/plan models, commands/queries, provider,
  and routes.
- `migrations/versions`: one reviewable analytics-domain migration after the
  template's initial auth migration.
- `docs`: ADR, permission matrix, metric dictionary, and API matrix.
- `tests/<module>`: pure unit tests plus DI/API/database integration tests.

## Security invariants

1. Organization and cabinet scope is derived from the authenticated user.
2. A client-provided cabinet list is intersected with server-side scope before
   repository access and before cache lookup.
3. Credentials are encrypted with AEAD and never serialized back to clients.
4. Background payloads contain job IDs, not tokens.
5. 400/401/403 are terminal or paused outcomes; 429, timeouts, and 5xx are
   bounded retries honoring `Retry-After`.

