# ADR-0001: Marketplace analytics as a modular monolith

**Status:** Accepted  
**Date:** 2026-08-03  
**Deciders:** Backend maintainers

## Context

The service must ingest seller data from Wildberries, Ozon, and Yandex Market,
retain auditable facts, calculate management metrics, and enforce organization
and cabinet-level access. The repository already provides async SQLAlchemy,
Alembic, Dishka, a command/query mediator, Taskiq, Redis, RBAC, logging, and
monitoring.

## Decision

Keep one deployable modular monolith with five business modules:
`organizations`, `marketplaces`, `catalog`, `analytics`, and `finance`.
HTTP writes use commands, reads use queries, and all handlers are resolved by
Dishka. Cross-module reads use explicit gateway interfaces. External seller
APIs are behind `MarketplaceConnectorInterface`; HTTP requests never occur in
analytics request handlers.

PostgreSQL is both the source of truth and the durable job/checkpoint store.
Raw normalized facts are immutable by business identity and are updated through
idempotent upserts. `analytics_daily` is the report-serving projection. Taskiq
executes ingestion and recomputation; Redis is only an acceleration layer.

Credentials use authenticated encryption at the application boundary. Queue
payloads contain only credential record identifiers.

## Options considered

| Option | Complexity | Consistency | Operational cost | Fit |
|---|---:|---:|---:|---|
| Modular monolith + durable DB jobs | Medium | Strong | Low | Chosen |
| Separate ingestion/analytics services | High | Eventual | High | Premature for current scale |
| Report directly from marketplace APIs | Low initially | Weak | Medium | Violates freshness, latency, and audit requirements |

## Consequences

- Module boundaries remain explicit without distributed transactions.
- A marketplace adapter can be replaced without changing orchestration.
- Report latency is stable because HTTP reads target daily projections.
- PostgreSQL schema and migration discipline become critical.
- Horizontal worker scaling requires the active-job uniqueness constraint and
  row locking to remain intact.

## Reusable repository components

- `BaseModel`, `DateMixin`, `SoftDeleteMixin`, async session and repositories.
- `BaseCommand`/`BaseQuery`, handler registries, and `DishkaMediator`.
- `BaseFilter`, `FilterMapper`, `find_by_filter`, and `PageResult`.
- `RBACManagerInterface`, the auth JWT DTO/dependencies, and cookie/JWT flow.
- `BaseTask`, `QueueService`, Taskiq broker/scheduler.
- Redis cache service, structlog context, Prometheus instrumentation, events,
  WebSocket service, and application exception envelope.

