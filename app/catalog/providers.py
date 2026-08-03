from dishka import Provider, Scope, decorate, provide

from app.catalog.application import (
    DeleteProductGroupCommand,
    DeleteProductGroupHandler,
    GetProductHandler,
    GetProductQuery,
    ImportProductCostsCommand,
    ImportProductCostsHandler,
    ListProductGroupsHandler,
    ListProductGroupsQuery,
    ListProductsHandler,
    ListProductsQuery,
    UpdateProductCommand,
    UpdateProductHandler,
    UpsertProductGroupCommand,
    UpsertProductGroupHandler,
)
from app.core.mediators.base import CommandRegistry, QueryRegistry


class CatalogProvider(Provider):
    scope = Scope.REQUEST

    list_products = provide(ListProductsHandler)
    get_product = provide(GetProductHandler)
    update_product = provide(UpdateProductHandler)
    import_costs = provide(ImportProductCostsHandler)
    list_groups = provide(ListProductGroupsHandler)
    upsert_group = provide(UpsertProductGroupHandler)
    delete_group = provide(DeleteProductGroupHandler)

    @decorate
    def commands(self, registry: CommandRegistry) -> CommandRegistry:
        registry.register_command(UpdateProductCommand, UpdateProductHandler)
        registry.register_command(ImportProductCostsCommand, ImportProductCostsHandler)
        registry.register_command(UpsertProductGroupCommand, UpsertProductGroupHandler)
        registry.register_command(DeleteProductGroupCommand, DeleteProductGroupHandler)
        return registry

    @decorate
    def queries(self, registry: QueryRegistry) -> QueryRegistry:
        registry.register_query(ListProductsQuery, ListProductsHandler)
        registry.register_query(GetProductQuery, GetProductHandler)
        registry.register_query(ListProductGroupsQuery, ListProductGroupsHandler)
        return registry
