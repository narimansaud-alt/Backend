import hashlib
from dataclasses import dataclass
from datetime import date
from uuid import UUID, uuid4

from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.commands import BaseCommand, BaseCommandHandler
from app.core.services.auth.dto import UserJWTData
from app.core.services.queues.service import QueueService
from app.core.utils import now_utc
from app.marketplaces.connectors import ConnectorFactory, MarketplaceAPIError
from app.marketplaces.credentials import CredentialCipher
from app.marketplaces.exceptions import (
    CabinetNotFoundError,
    MarketplaceRequestError,
    SyncConflictError,
    UnsupportedSyncKindError,
)
from app.marketplaces.models import (
    Marketplace,
    MarketplaceCabinet,
    MarketplaceCredential,
    SyncJob,
    SyncKind,
    SyncStatus,
)
from app.marketplaces.repositories import CabinetRepository, SyncJobRepository, get_credential
from app.marketplaces.retry import split_period
from app.marketplaces.schemas import (
    CabinetResponse,
    CredentialValidationResponse,
    SyncJobResponse,
    SyncStartResponse,
)
from app.marketplaces.tasks import RunSyncJobTask
from app.organizations.exceptions import OrganizationForbiddenError
from app.organizations.services import OrganizationScopeService


async def _require_cabinet(
    cabinet_id: UUID,
    user: UserJWTData,
    permission: str,
    repository: CabinetRepository,
    scope_service: OrganizationScopeService,
) -> MarketplaceCabinet:
    cabinet = await repository.get(cabinet_id)
    if cabinet is None:
        raise CabinetNotFoundError
    try:
        scope = await scope_service.require(int(user.id), cabinet.organization_id, permission)
    except PermissionError as exc:
        raise CabinetNotFoundError from exc
    allowed = scope.restrict_cabinets({cabinet.id})
    if allowed is not None and cabinet.id not in allowed:
        raise CabinetNotFoundError
    return cabinet


@dataclass(frozen=True)
class CreateCabinetCommand(BaseCommand):
    user: UserJWTData
    organization_id: UUID
    marketplace: Marketplace
    external_id: str
    name: str
    credential: str


@dataclass(frozen=True)
class CreateCabinetHandler(BaseCommandHandler[CreateCabinetCommand, CabinetResponse]):
    session: AsyncSession
    scope_service: OrganizationScopeService
    connector_factory: ConnectorFactory
    credential_cipher: CredentialCipher

    async def handle(self, command: CreateCabinetCommand) -> CabinetResponse:
        try:
            await self.scope_service.require(int(command.user.id), command.organization_id, "cabinet:manage")
        except PermissionError as exc:
            raise OrganizationForbiddenError(permission="cabinet:manage") from exc
        connector = self.connector_factory.get(command.marketplace)
        try:
            validation = await connector.validate_credentials(command.credential, command.external_id)
        except MarketplaceAPIError as exc:
            raise MarketplaceRequestError(error_code=exc.code, safe_message=exc.safe_message) from exc
        cabinet_id = uuid4()
        encrypted = self.credential_cipher.encrypt(command.credential, cabinet_id=str(cabinet_id))
        cabinet = MarketplaceCabinet(
            id=cabinet_id,
            organization_id=command.organization_id,
            marketplace=command.marketplace,
            external_id=command.external_id,
            name=command.name,
        )
        credential = MarketplaceCredential(
            cabinet_id=cabinet_id,
            encrypted_value=encrypted.value,
            key_version=encrypted.key_version,
            scopes=sorted(validation.scopes),
            masked_hint=encrypted.masked_hint,
            validated_at=now_utc(),
        )
        self.session.add_all((cabinet, credential))
        await self.session.commit()
        response = CabinetResponse.model_validate(cabinet)
        return response.model_copy(
            update={
                "credential_masked_hint": credential.masked_hint,
                "credential_scopes": credential.scopes,
                "credential_validated_at": credential.validated_at,
            }
        )


@dataclass(frozen=True)
class UpdateCabinetCommand(BaseCommand):
    user: UserJWTData
    cabinet_id: UUID
    name: str | None
    is_active: bool | None


@dataclass(frozen=True)
class UpdateCabinetHandler(BaseCommandHandler[UpdateCabinetCommand, CabinetResponse]):
    session: AsyncSession
    repository: CabinetRepository
    scope_service: OrganizationScopeService

    async def handle(self, command: UpdateCabinetCommand) -> CabinetResponse:
        cabinet = await _require_cabinet(
            command.cabinet_id, command.user, "cabinet:manage", self.repository, self.scope_service
        )
        if command.name is not None:
            cabinet.name = command.name
        if command.is_active is not None:
            cabinet.is_active = command.is_active
        await self.session.commit()
        return CabinetResponse.model_validate(cabinet)


@dataclass(frozen=True)
class DeleteCabinetCommand(BaseCommand):
    user: UserJWTData
    cabinet_id: UUID


@dataclass(frozen=True)
class DeleteCabinetHandler(BaseCommandHandler[DeleteCabinetCommand, None]):
    session: AsyncSession
    repository: CabinetRepository
    scope_service: OrganizationScopeService

    async def handle(self, command: DeleteCabinetCommand) -> None:
        cabinet = await _require_cabinet(
            command.cabinet_id, command.user, "cabinet:manage", self.repository, self.scope_service
        )
        cabinet.is_active = False
        cabinet.soft_delete()
        await self.session.commit()


@dataclass(frozen=True)
class ValidateCredentialCommand(BaseCommand):
    user: UserJWTData
    cabinet_id: UUID
    new_credential: str | None


@dataclass(frozen=True)
class ValidateCredentialHandler(BaseCommandHandler[ValidateCredentialCommand, CredentialValidationResponse]):
    session: AsyncSession
    repository: CabinetRepository
    scope_service: OrganizationScopeService
    connector_factory: ConnectorFactory
    credential_cipher: CredentialCipher

    async def handle(self, command: ValidateCredentialCommand) -> CredentialValidationResponse:
        cabinet = await _require_cabinet(
            command.cabinet_id, command.user, "cabinet:manage", self.repository, self.scope_service
        )
        stored = await get_credential(self.session, cabinet.id)
        if stored is None and command.new_credential is None:
            raise MarketplaceRequestError(error_code="TOKEN_INVALID", safe_message="Cabinet has no credential")
        secret = command.new_credential
        if secret is None:
            assert stored is not None
            secret = self.credential_cipher.decrypt(
                stored.encrypted_value, key_version=stored.key_version, cabinet_id=str(cabinet.id)
            )
        connector = self.connector_factory.get(cabinet.marketplace)
        try:
            validation = await connector.validate_credentials(secret, cabinet.external_id)
        except MarketplaceAPIError as exc:
            if stored is not None:
                stored.validation_error_code = exc.code
                await self.session.commit()
            raise MarketplaceRequestError(error_code=exc.code, safe_message=exc.safe_message) from exc
        if command.new_credential is not None:
            encrypted = self.credential_cipher.encrypt(secret, cabinet_id=str(cabinet.id))
            if stored is None:
                stored = MarketplaceCredential(
                    cabinet_id=cabinet.id,
                    encrypted_value=encrypted.value,
                    key_version=encrypted.key_version,
                    masked_hint=encrypted.masked_hint,
                )
                self.session.add(stored)
            else:
                stored.encrypted_value = encrypted.value
                stored.key_version = encrypted.key_version
                stored.masked_hint = encrypted.masked_hint
                stored.revision += 1
        assert stored is not None
        stored.scopes = sorted(validation.scopes)
        stored.validated_at = now_utc()
        stored.validation_error_code = None
        await self.session.commit()
        return CredentialValidationResponse(
            masked_hint=stored.masked_hint, scopes=stored.scopes, validated_at=stored.validated_at
        )


MAX_WINDOW_DAYS: dict[tuple[Marketplace, SyncKind], int] = {
    (Marketplace.WILDBERRIES, SyncKind.ANALYTICS_FUNNEL): 7,
    (Marketplace.OZON, SyncKind.FINANCE_TRANSACTIONS): 31,
    (Marketplace.YANDEX_MARKET, SyncKind.ORDERS): 30,
}


@dataclass(frozen=True)
class StartSyncCommand(BaseCommand):
    user: UserJWTData
    cabinet_id: UUID
    kinds: frozenset[SyncKind]
    date_from: date
    date_to: date


@dataclass(frozen=True)
class StartSyncHandler(BaseCommandHandler[StartSyncCommand, SyncStartResponse]):
    session: AsyncSession
    repository: CabinetRepository
    scope_service: OrganizationScopeService
    connector_factory: ConnectorFactory
    queue: QueueService

    async def handle(self, command: StartSyncCommand) -> SyncStartResponse:
        cabinet = await _require_cabinet(
            command.cabinet_id, command.user, "cabinet:sync", self.repository, self.scope_service
        )
        connector = self.connector_factory.get(cabinet.marketplace)
        for kind in command.kinds:
            if kind not in connector.supported_kinds:
                raise UnsupportedSyncKindError(marketplace=cabinet.marketplace, kind=kind)
        job_ids: list[UUID] = []
        for kind in sorted(command.kinds, key=str):
            windows = split_period(
                command.date_from, command.date_to, MAX_WINDOW_DAYS.get((Marketplace(cabinet.marketplace), kind), 31)
            )
            for period_from, period_to in windows:
                identity = f"{cabinet.id}:{kind}:{period_from}:{period_to}"
                job_id = uuid4()
                stmt = (
                    insert(SyncJob)
                    .values(
                        id=job_id,
                        organization_id=cabinet.organization_id,
                        cabinet_id=cabinet.id,
                        kind=kind,
                        period_from=period_from,
                        period_to=period_to,
                        status=SyncStatus.QUEUED,
                        stage="queued",
                        idempotency_key=hashlib.sha256(identity.encode()).hexdigest(),
                    )
                    .on_conflict_do_nothing(index_elements=[SyncJob.idempotency_key])
                    .returning(SyncJob.id)
                )
                created_id = await self.session.scalar(stmt)
                if created_id is not None:
                    job_ids.append(created_id)
        await self.session.commit()
        if not job_ids:
            raise SyncConflictError
        for job_id in job_ids:
            await self.queue.push(RunSyncJobTask, {"job_id": str(job_id)})
        return SyncStartResponse(job_ids=job_ids)


@dataclass(frozen=True)
class RetrySyncCommand(BaseCommand):
    user: UserJWTData
    job_id: UUID


@dataclass(frozen=True)
class RetrySyncHandler(BaseCommandHandler[RetrySyncCommand, SyncJobResponse]):
    session: AsyncSession
    repository: SyncJobRepository
    cabinet_repository: CabinetRepository
    scope_service: OrganizationScopeService
    queue: QueueService

    async def handle(self, command: RetrySyncCommand) -> SyncJobResponse:
        job = await self.repository.get(command.job_id)
        if job is None:
            raise CabinetNotFoundError
        await _require_cabinet(
            job.cabinet_id, command.user, "cabinet:sync", self.cabinet_repository, self.scope_service
        )
        if job.status not in {SyncStatus.FAILED, SyncStatus.PAUSED, SyncStatus.RETRY_WAIT}:
            raise SyncConflictError
        job.status = SyncStatus.QUEUED
        job.stage = "queued"
        job.error_code = None
        job.error_message = None
        job.next_retry_at = None
        await self.session.commit()
        await self.queue.push(RunSyncJobTask, {"job_id": str(job.id)})
        return SyncJobResponse.model_validate(job)
