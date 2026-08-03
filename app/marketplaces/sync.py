import logging
import time
from dataclasses import dataclass
from datetime import timedelta
from decimal import Decimal
from typing import Any, cast
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.analytics.models import FinanceTransactionFact, OrderFact, ReturnFact, SaleFact
from app.analytics.projections import AnalyticsProjectionService
from app.catalog.models import MarketplaceOffer
from app.core.utils import now_utc
from app.marketplaces.config import marketplace_config
from app.marketplaces.connectors import ConnectorFactory, MarketplaceAPIError
from app.marketplaces.credentials import CredentialCipher
from app.marketplaces.metrics import (
    SYNC_DURATION,
    SYNC_IN_PROGRESS,
    SYNC_JOBS,
    SYNC_LAST_SUCCESS,
    SYNC_RECORDS,
)
from app.marketplaces.models import (
    Marketplace,
    MarketplaceCabinet,
    MarketplaceCredential,
    SyncCheckpoint,
    SyncJob,
    SyncJobEvent,
    SyncKind,
    SyncStatus,
)
from app.marketplaces.normalizers import CanonicalRecord, normalize_record
from app.marketplaces.retry import RetryAction, retry_decision

logger = logging.getLogger(__name__)


@dataclass
class FactWriter:
    session: AsyncSession

    async def _product_id(self, cabinet_id: UUID, external_offer_id: str | None) -> UUID | None:
        if not external_offer_id:
            return None
        return cast(
            UUID | None,
            await self.session.scalar(
                select(MarketplaceOffer.product_id).where(
                    MarketplaceOffer.cabinet_id == cabinet_id,
                    MarketplaceOffer.external_offer_id == external_offer_id,
                )
            ),
        )

    async def upsert(
        self,
        *,
        job: SyncJob,
        marketplace: Marketplace,
        record: CanonicalRecord,
    ) -> None:
        product_id = await self._product_id(job.cabinet_id, record.external_offer_id)
        common = {
            "organization_id": job.organization_id,
            "cabinet_id": job.cabinet_id,
            "product_id": product_id,
            "marketplace": marketplace.value,
            "external_key": record.external_key,
            "business_date": record.business_date,
            "source_updated_at": record.source_updated_at,
        }
        kind = SyncKind(job.kind)
        if kind is SyncKind.ORDERS:
            model: Any = OrderFact
            values: dict[str, Any] = {
                **common,
                "quantity": record.quantity,
                "amount": record.amount,
                "source_payload": {},
            }
            updates = {
                key: values[key] for key in ("business_date", "quantity", "amount", "source_updated_at", "product_id")
            }
        elif kind is SyncKind.SALES_RETURNS:
            model = ReturnFact if record.operation_type == "return" else SaleFact
            values = {**common, "quantity": abs(record.quantity), "amount": abs(record.amount), "source_payload": {}}
            updates = {
                key: values[key] for key in ("business_date", "quantity", "amount", "source_updated_at", "product_id")
            }
        elif kind is SyncKind.FINANCE_TRANSACTIONS:
            model = FinanceTransactionFact
            values = {
                **common,
                "amount": record.amount,
                "operation_type": record.operation_type or "other",
                "source_payload": {},
            }
            updates = {
                key: values[key]
                for key in ("business_date", "amount", "operation_type", "source_updated_at", "product_id")
            }
        else:
            raise ValueError(f"No fact writer for sync kind {job.kind}")
        stmt = (
            insert(model)
            .values(**values)
            .on_conflict_do_update(
                index_elements=[model.marketplace, model.cabinet_id, model.external_key],
                set_=updates,
            )
        )
        await self.session.execute(stmt)


@dataclass
class SyncJobRunner:
    session: AsyncSession
    connector_factory: ConnectorFactory
    credential_cipher: CredentialCipher
    fact_writer: FactWriter
    projection_service: AnalyticsProjectionService

    async def run(self, job_id: str) -> None:
        job = await self.session.scalar(
            select(SyncJob).where(SyncJob.id == UUID(job_id)).with_for_update(skip_locked=True)
        )
        if job is None or job.status not in {SyncStatus.QUEUED, SyncStatus.RETRY_WAIT}:
            return
        cabinet = await self.session.get(MarketplaceCabinet, job.cabinet_id)
        credential = await self.session.scalar(
            select(MarketplaceCredential).where(MarketplaceCredential.cabinet_id == job.cabinet_id)
        )
        if cabinet is None or credential is None:
            await self._fail(job, "TOKEN_INVALID", "Cabinet credential is unavailable", pause=True)
            return
        secret = self.credential_cipher.decrypt(
            credential.encrypted_value,
            key_version=credential.key_version,
            cabinet_id=str(cabinet.id),
        )
        connector = self.connector_factory.get(cabinet.marketplace)
        metric_labels = (str(cabinet.marketplace), str(job.kind))
        started = time.monotonic()
        SYNC_IN_PROGRESS.labels(*metric_labels).inc()
        job.status = SyncStatus.RUNNING
        job.stage = "fetching"
        job.started_at = job.started_at or now_utc()
        job.attempts += 1
        await self.session.commit()
        cursor = job.cursor
        seen_cursors: set[str] = set()
        try:
            for _ in range(10_000):
                page = await connector.fetch_page(
                    kind=SyncKind(job.kind),
                    credential=secret,
                    external_id=cabinet.external_id,
                    date_from=job.period_from,
                    date_to=job.period_to,
                    cursor=cursor,
                )
                written = 0
                for source in page.records:
                    for normalized in normalize_record(Marketplace(cabinet.marketplace), SyncKind(job.kind), source):
                        await self.fact_writer.upsert(
                            job=job,
                            marketplace=Marketplace(cabinet.marketplace),
                            record=normalized,
                        )
                        written += 1
                SYNC_RECORDS.labels(*metric_labels).inc(written)
                job.rows_processed += written
                cursor = page.next_cursor
                job.cursor = cursor
                checkpoint = await self.session.scalar(
                    select(SyncCheckpoint).where(
                        SyncCheckpoint.job_id == job.id,
                        SyncCheckpoint.endpoint_group == job.kind,
                    )
                )
                if checkpoint is None:
                    checkpoint = SyncCheckpoint(
                        job_id=job.id,
                        endpoint_group=job.kind,
                        cursor=cursor or {},
                        rows_processed=job.rows_processed,
                    )
                    self.session.add(checkpoint)
                else:
                    checkpoint.cursor = cursor or {}
                    checkpoint.page_number += 1
                    checkpoint.rows_processed = job.rows_processed
                await self.session.commit()
                if cursor is None:
                    break
                cursor_key = repr(sorted(cursor.items()))
                if cursor_key in seen_cursors:
                    raise RuntimeError("Marketplace cursor did not advance")
                seen_cursors.add(cursor_key)
            else:
                raise RuntimeError("Marketplace pagination exceeded the safety limit")
        except MarketplaceAPIError as exc:
            decision = retry_decision(
                status_code=exc.status_code,
                attempt=job.attempts,
                max_attempts=marketplace_config.MARKETPLACE_MAX_RETRIES,
                retry_after=exc.retry_after,
            )
            if decision.action is RetryAction.RETRY:
                job.status = SyncStatus.RETRY_WAIT
                job.stage = "retry_wait"
                job.error_code = decision.code
                job.error_message = exc.safe_message
                job.next_retry_at = now_utc() + timedelta(seconds=decision.delay_seconds or 0)
                await self._event(job, "warning", decision.code, exc.safe_message)
                await self.session.commit()
                self._observe(job, metric_labels, started, "retry_wait")
                return
            await self._fail(job, decision.code, exc.safe_message, pause=decision.action is RetryAction.PAUSE)
            self._observe(job, metric_labels, started, "paused" if decision.action is RetryAction.PAUSE else "failed")
            return
        except Exception:
            logger.exception(
                "Synchronization job failed",
                extra={"job_id": str(job.id), "cabinet_id": str(job.cabinet_id), "kind": job.kind},
            )
            await self._fail(job, "SYNC_INTERNAL_ERROR", "Synchronization failed", pause=False)
            self._observe(job, metric_labels, started, "failed")
            return
        try:
            await self.projection_service.recompute(job)
        except Exception:  # noqa: BLE001 -- projection failure must become a terminal job state
            logger.exception(
                "Analytics projection failed",
                extra={"job_id": str(job.id), "cabinet_id": str(job.cabinet_id), "kind": job.kind},
            )
            await self._fail(job, "PROJECTION_FAILED", "Analytics projection failed", pause=False)
            self._observe(job, metric_labels, started, "failed")
            return
        job.status = SyncStatus.SUCCEEDED
        job.stage = "complete"
        job.progress = Decimal("100")
        job.finished_at = now_utc()
        job.error_code = None
        job.error_message = None
        await self._event(job, "info", "SYNC_SUCCEEDED", "Synchronization completed")
        await self.session.commit()
        SYNC_LAST_SUCCESS.labels(*metric_labels, str(job.cabinet_id)).set(now_utc().timestamp())
        self._observe(job, metric_labels, started, "succeeded")

    @staticmethod
    def _observe(
        job: SyncJob,
        metric_labels: tuple[str, str],
        started: float,
        result: str,
    ) -> None:
        SYNC_IN_PROGRESS.labels(*metric_labels).dec()
        SYNC_DURATION.labels(*metric_labels).observe(time.monotonic() - started)
        SYNC_JOBS.labels(*metric_labels, result).inc()

    async def _event(self, job: SyncJob, level: str, code: str, message: str) -> None:
        latest = await self.session.scalar(
            select(SyncJobEvent)
            .where(
                SyncJobEvent.job_id == job.id,
                SyncJobEvent.code == code,
            )
            .order_by(SyncJobEvent.created_at.desc())
        )
        if latest is None or latest.safe_message != message:
            self.session.add(
                SyncJobEvent(
                    job_id=job.id,
                    level=level,
                    code=code,
                    safe_message=message[:512],
                    details={"attempt": job.attempts},
                )
            )
        else:
            job.repeated_error_count += 1

    async def _fail(self, job: SyncJob, code: str, message: str, *, pause: bool) -> None:
        job.status = SyncStatus.PAUSED if pause else SyncStatus.FAILED
        job.stage = "paused" if pause else "failed"
        job.error_code = code
        job.error_message = message[:512]
        job.finished_at = now_utc()
        await self._event(job, "error", code, message)
        await self.session.commit()
