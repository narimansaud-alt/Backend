from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.catalog.models import Product, ProductCostHistory, ProductGroup
from app.catalog.schemas import (
    ProductCostImportRow,
    ProductGroupResponse,
    ProductResponse,
)
from app.core.commands import BaseCommand, BaseCommandHandler
from app.core.db.repository import PageResult
from app.core.queries import BaseQuery, BaseQueryHandler
from app.core.services.auth.dto import UserJWTData
from app.organizations.exceptions import OrganizationForbiddenError, OrganizationNotFoundError
from app.organizations.services import OrganizationScopeService


@dataclass(frozen=True)
class ListProductsQuery(BaseQuery):
    user: UserJWTData
    organization_id: UUID
    page: int
    page_size: int


@dataclass(frozen=True)
class ListProductsHandler(BaseQueryHandler[ListProductsQuery, PageResult[ProductResponse]]):
    session: AsyncSession
    scope_service: OrganizationScopeService

    async def handle(self, query: ListProductsQuery) -> PageResult[ProductResponse]:
        try:
            await self.scope_service.require(int(query.user.id), query.organization_id, "analytics:view")
        except PermissionError as exc:
            raise OrganizationForbiddenError(permission="analytics:view") from exc
        base = Product.select_not_deleted().where(Product.organization_id == query.organization_id)
        total = await self.session.scalar(select(func.count()).select_from(base.subquery())) or 0
        rows = (
            await self.session.scalars(
                base.order_by(Product.internal_sku).offset((query.page - 1) * query.page_size).limit(query.page_size)
            )
        ).all()
        return PageResult(
            items=[ProductResponse.model_validate(row) for row in rows],
            total=total,
            page=query.page,
            page_size=query.page_size,
        )


@dataclass(frozen=True)
class GetProductQuery(BaseQuery):
    user: UserJWTData
    product_id: UUID


@dataclass(frozen=True)
class GetProductHandler(BaseQueryHandler[GetProductQuery, ProductResponse]):
    session: AsyncSession
    scope_service: OrganizationScopeService

    async def handle(self, query: GetProductQuery) -> ProductResponse:
        product = await self.session.scalar(Product.select_not_deleted().where(Product.id == query.product_id))
        if product is None:
            raise OrganizationNotFoundError
        try:
            await self.scope_service.require(int(query.user.id), product.organization_id, "analytics:view")
        except PermissionError as exc:
            raise OrganizationNotFoundError from exc
        return ProductResponse.model_validate(product)


@dataclass(frozen=True)
class UpdateProductCommand(BaseCommand):
    user: UserJWTData
    product_id: UUID
    name: str | None
    group_id: UUID | None


@dataclass(frozen=True)
class UpdateProductHandler(BaseCommandHandler[UpdateProductCommand, ProductResponse]):
    session: AsyncSession
    scope_service: OrganizationScopeService

    async def handle(self, command: UpdateProductCommand) -> ProductResponse:
        product = await self.session.scalar(Product.select_not_deleted().where(Product.id == command.product_id))
        if product is None:
            raise OrganizationNotFoundError
        try:
            await self.scope_service.require(int(command.user.id), product.organization_id, "cost:manage")
        except PermissionError as exc:
            raise OrganizationNotFoundError from exc
        if command.name is not None:
            product.name = command.name
        product.group_id = command.group_id
        await self.session.commit()
        return ProductResponse.model_validate(product)


@dataclass(frozen=True)
class ImportProductCostsCommand(BaseCommand):
    user: UserJWTData
    organization_id: UUID
    rows: tuple[ProductCostImportRow, ...]


@dataclass(frozen=True)
class ImportProductCostsHandler(BaseCommandHandler[ImportProductCostsCommand, int]):
    session: AsyncSession
    scope_service: OrganizationScopeService

    async def handle(self, command: ImportProductCostsCommand) -> int:
        try:
            await self.scope_service.require(int(command.user.id), command.organization_id, "cost:manage")
        except PermissionError as exc:
            raise OrganizationForbiddenError(permission="cost:manage") from exc
        product_ids = {row.product_id for row in command.rows}
        owned = set(
            (
                await self.session.scalars(
                    select(Product.id).where(
                        Product.organization_id == command.organization_id, Product.id.in_(product_ids)
                    )
                )
            ).all()
        )
        if owned != product_ids:
            raise OrganizationNotFoundError
        for row in command.rows:
            if row.valid_to is not None and row.valid_to < row.valid_from:
                raise ValueError("Cost valid_to must not precede valid_from")
            stmt = (
                insert(ProductCostHistory)
                .values(**row.model_dump())
                .on_conflict_do_update(
                    index_elements=[ProductCostHistory.product_id, ProductCostHistory.valid_from],
                    set_={"valid_to": row.valid_to, "unit_cost": row.unit_cost, "currency": row.currency},
                )
            )
            await self.session.execute(stmt)
        await self.session.commit()
        return len(command.rows)


@dataclass(frozen=True)
class ListProductGroupsQuery(BaseQuery):
    user: UserJWTData
    organization_id: UUID


@dataclass(frozen=True)
class ListProductGroupsHandler(BaseQueryHandler[ListProductGroupsQuery, list[ProductGroupResponse]]):
    session: AsyncSession
    scope_service: OrganizationScopeService

    async def handle(self, query: ListProductGroupsQuery) -> list[ProductGroupResponse]:
        try:
            await self.scope_service.require(int(query.user.id), query.organization_id, "analytics:view")
        except PermissionError as exc:
            raise OrganizationForbiddenError(permission="analytics:view") from exc
        rows = (
            await self.session.scalars(
                ProductGroup.select_not_deleted()
                .where(ProductGroup.organization_id == query.organization_id)
                .order_by(ProductGroup.name)
            )
        ).all()
        return [ProductGroupResponse.model_validate(row) for row in rows]


@dataclass(frozen=True)
class UpsertProductGroupCommand(BaseCommand):
    user: UserJWTData
    organization_id: UUID
    group_id: UUID | None
    name: str


@dataclass(frozen=True)
class UpsertProductGroupHandler(BaseCommandHandler[UpsertProductGroupCommand, ProductGroupResponse]):
    session: AsyncSession
    scope_service: OrganizationScopeService

    async def handle(self, command: UpsertProductGroupCommand) -> ProductGroupResponse:
        try:
            await self.scope_service.require(int(command.user.id), command.organization_id, "cost:manage")
        except PermissionError as exc:
            raise OrganizationForbiddenError(permission="cost:manage") from exc
        group = None
        if command.group_id is not None:
            group = await self.session.scalar(
                ProductGroup.select_not_deleted().where(
                    ProductGroup.id == command.group_id,
                    ProductGroup.organization_id == command.organization_id,
                )
            )
            if group is None:
                raise OrganizationNotFoundError
            group.name = command.name
        else:
            group = ProductGroup(organization_id=command.organization_id, name=command.name)
            self.session.add(group)
        await self.session.commit()
        return ProductGroupResponse.model_validate(group)


@dataclass(frozen=True)
class DeleteProductGroupCommand(BaseCommand):
    user: UserJWTData
    organization_id: UUID
    group_id: UUID


@dataclass(frozen=True)
class DeleteProductGroupHandler(BaseCommandHandler[DeleteProductGroupCommand, None]):
    session: AsyncSession
    scope_service: OrganizationScopeService

    async def handle(self, command: DeleteProductGroupCommand) -> None:
        try:
            await self.scope_service.require(int(command.user.id), command.organization_id, "cost:manage")
        except PermissionError as exc:
            raise OrganizationForbiddenError(permission="cost:manage") from exc
        group = await self.session.scalar(
            ProductGroup.select_not_deleted().where(
                ProductGroup.id == command.group_id,
                ProductGroup.organization_id == command.organization_id,
            )
        )
        if group is None:
            raise OrganizationNotFoundError
        group.soft_delete()
        await self.session.commit()
