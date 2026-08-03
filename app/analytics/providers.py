from dishka import Provider, Scope, decorate, provide

from app.analytics.client_error_queries import ListClientErrorsHandler, ListClientErrorsQuery
from app.analytics.commands import RecordClientErrorCommand, RecordClientErrorHandler
from app.analytics.exports import (
    CreateExportCommand,
    CreateExportHandler,
    ExportRunner,
    GetExportHandler,
    GetExportQuery,
)
from app.analytics.projections import AnalyticsProjectionService
from app.analytics.queries import (
    GetAnalyticsOverviewHandler,
    GetAnalyticsOverviewQuery,
    GetAnalyticsTimeSeriesHandler,
    GetAnalyticsTimeSeriesQuery,
)
from app.core.mediators.base import CommandRegistry, QueryRegistry


class AnalyticsProvider(Provider):
    scope = Scope.REQUEST

    projection_service = provide(AnalyticsProjectionService)
    overview = provide(GetAnalyticsOverviewHandler)
    timeseries = provide(GetAnalyticsTimeSeriesHandler)
    record_client_error = provide(RecordClientErrorHandler)
    list_client_errors = provide(ListClientErrorsHandler)
    create_export = provide(CreateExportHandler)
    get_export = provide(GetExportHandler)
    export_runner = provide(ExportRunner)

    @decorate
    def commands(self, registry: CommandRegistry) -> CommandRegistry:
        registry.register_command(RecordClientErrorCommand, RecordClientErrorHandler)
        registry.register_command(CreateExportCommand, CreateExportHandler)
        return registry

    @decorate
    def queries(self, registry: QueryRegistry) -> QueryRegistry:
        registry.register_query(GetAnalyticsOverviewQuery, GetAnalyticsOverviewHandler)
        registry.register_query(GetAnalyticsTimeSeriesQuery, GetAnalyticsTimeSeriesHandler)
        registry.register_query(ListClientErrorsQuery, ListClientErrorsHandler)
        registry.register_query(GetExportQuery, GetExportHandler)
        return registry
