from collections.abc import AsyncIterable

import httpx
from dishka import Provider, Scope, decorate, provide

from app.core.mediators.base import CommandRegistry, QueryRegistry
from app.marketplaces.commands import (
    CreateCabinetCommand,
    CreateCabinetHandler,
    DeleteCabinetCommand,
    DeleteCabinetHandler,
    RetrySyncCommand,
    RetrySyncHandler,
    StartSyncCommand,
    StartSyncHandler,
    UpdateCabinetCommand,
    UpdateCabinetHandler,
    ValidateCredentialCommand,
    ValidateCredentialHandler,
)
from app.marketplaces.config import marketplace_config
from app.marketplaces.connectors import (
    ConnectorFactory,
    OzonConnector,
    WildberriesConnector,
    YandexMarketConnector,
)
from app.marketplaces.credentials import CredentialCipher
from app.marketplaces.queries import (
    GetCabinetHandler,
    GetCabinetQuery,
    GetSyncJobHandler,
    GetSyncJobQuery,
    GetSyncOverviewHandler,
    GetSyncOverviewQuery,
    ListCabinetsHandler,
    ListCabinetsQuery,
    ListSyncJobsHandler,
    ListSyncJobsQuery,
)
from app.marketplaces.repositories import CabinetRepository, SyncJobRepository
from app.marketplaces.sync import FactWriter, SyncJobRunner


class MarketplacesProvider(Provider):
    scope = Scope.REQUEST

    cabinet_repository = provide(CabinetRepository)
    sync_job_repository = provide(SyncJobRepository)
    fact_writer = provide(FactWriter)
    sync_runner = provide(SyncJobRunner)

    create_cabinet = provide(CreateCabinetHandler)
    update_cabinet = provide(UpdateCabinetHandler)
    delete_cabinet = provide(DeleteCabinetHandler)
    validate_credential = provide(ValidateCredentialHandler)
    start_sync = provide(StartSyncHandler)
    retry_sync = provide(RetrySyncHandler)

    list_cabinets = provide(ListCabinetsHandler)
    get_cabinet = provide(GetCabinetHandler)
    list_sync_jobs = provide(ListSyncJobsHandler)
    get_sync_job = provide(GetSyncJobHandler)
    get_sync_overview = provide(GetSyncOverviewHandler)

    @provide(scope=Scope.APP)
    async def http_client(self) -> AsyncIterable[httpx.AsyncClient]:
        async with httpx.AsyncClient(
            timeout=httpx.Timeout(marketplace_config.MARKETPLACE_HTTP_TIMEOUT_SECONDS),
            follow_redirects=False,
            headers={"User-Agent": "marketplace-analytics/1.0"},
        ) as client:
            yield client

    @provide(scope=Scope.APP)
    def credential_cipher(self) -> CredentialCipher:
        return CredentialCipher(
            encoded_keys=marketplace_config.CREDENTIAL_ENCRYPTION_KEYS,
            active_key_version=marketplace_config.CREDENTIAL_ACTIVE_KEY_VERSION,
        )

    @provide(scope=Scope.APP)
    def connector_factory(self, client: httpx.AsyncClient) -> ConnectorFactory:
        connectors = (
            WildberriesConnector(client),
            OzonConnector(client),
            YandexMarketConnector(client),
        )
        return ConnectorFactory({connector.marketplace: connector for connector in connectors})

    @decorate
    def commands(self, registry: CommandRegistry) -> CommandRegistry:
        registry.register_command(CreateCabinetCommand, CreateCabinetHandler)
        registry.register_command(UpdateCabinetCommand, UpdateCabinetHandler)
        registry.register_command(DeleteCabinetCommand, DeleteCabinetHandler)
        registry.register_command(ValidateCredentialCommand, ValidateCredentialHandler)
        registry.register_command(StartSyncCommand, StartSyncHandler)
        registry.register_command(RetrySyncCommand, RetrySyncHandler)
        return registry

    @decorate
    def queries(self, registry: QueryRegistry) -> QueryRegistry:
        registry.register_query(ListCabinetsQuery, ListCabinetsHandler)
        registry.register_query(GetCabinetQuery, GetCabinetHandler)
        registry.register_query(ListSyncJobsQuery, ListSyncJobsHandler)
        registry.register_query(GetSyncJobQuery, GetSyncJobHandler)
        registry.register_query(GetSyncOverviewQuery, GetSyncOverviewHandler)
        return registry
