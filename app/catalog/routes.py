from typing import Annotated
from uuid import UUID

from dishka import FromDishka
from dishka.integrations.fastapi import DishkaRoute
from fastapi import APIRouter, Query, status

from app.auth.deps import AuthCurrentUserJWTData
from app.catalog.application import (
    DeleteProductGroupCommand,
    GetProductQuery,
    ImportProductCostsCommand,
    ListProductGroupsQuery,
    ListProductsQuery,
    UpdateProductCommand,
    UpsertProductGroupCommand,
)
from app.catalog.schemas import (
    ProductCostImportRequest,
    ProductGroupCreateRequest,
    ProductGroupResponse,
    ProductGroupUpdateRequest,
    ProductResponse,
    ProductUpdateRequest,
)
from app.core.db.repository import PageResult
from app.core.mediators.base import BaseMediator

router = APIRouter(tags=["catalog"], route_class=DishkaRoute)


@router.get("/products")
async def list_products(
    organization_id: UUID,
    mediator: FromDishka[BaseMediator],
    user: AuthCurrentUserJWTData,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> PageResult[ProductResponse]:
    return await mediator.handle_query(
        ListProductsQuery(user=user, organization_id=organization_id, page=page, page_size=page_size)
    )


@router.get("/products/{product_id}")
async def get_product(
    product_id: UUID, mediator: FromDishka[BaseMediator], user: AuthCurrentUserJWTData
) -> ProductResponse:
    return await mediator.handle_query(GetProductQuery(user=user, product_id=product_id))


@router.patch("/products/{product_id}")
async def update_product(
    product_id: UUID, request: ProductUpdateRequest, mediator: FromDishka[BaseMediator], user: AuthCurrentUserJWTData
) -> ProductResponse:
    return await mediator.handle_command(UpdateProductCommand(user=user, product_id=product_id, **request.model_dump()))


@router.post("/products/costs/import")
async def import_product_costs(
    request: ProductCostImportRequest, mediator: FromDishka[BaseMediator], user: AuthCurrentUserJWTData
) -> dict[str, int]:
    imported: int = await mediator.handle_command(
        ImportProductCostsCommand(user=user, organization_id=request.organization_id, rows=tuple(request.rows))
    )
    return {"imported": imported}


@router.get("/product-groups")
async def list_product_groups(
    organization_id: UUID, mediator: FromDishka[BaseMediator], user: AuthCurrentUserJWTData
) -> list[ProductGroupResponse]:
    return await mediator.handle_query(ListProductGroupsQuery(user=user, organization_id=organization_id))


@router.post("/product-groups", status_code=status.HTTP_201_CREATED)
async def create_product_group(
    request: ProductGroupCreateRequest, mediator: FromDishka[BaseMediator], user: AuthCurrentUserJWTData
) -> ProductGroupResponse:
    return await mediator.handle_command(UpsertProductGroupCommand(user=user, group_id=None, **request.model_dump()))


@router.patch("/product-groups/{group_id}")
async def update_product_group(
    group_id: UUID,
    organization_id: UUID,
    request: ProductGroupUpdateRequest,
    mediator: FromDishka[BaseMediator],
    user: AuthCurrentUserJWTData,
) -> ProductGroupResponse:
    return await mediator.handle_command(
        UpsertProductGroupCommand(user=user, organization_id=organization_id, group_id=group_id, name=request.name)
    )


@router.delete("/product-groups/{group_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_product_group(
    group_id: UUID,
    organization_id: UUID,
    mediator: FromDishka[BaseMediator],
    user: AuthCurrentUserJWTData,
) -> None:
    await mediator.handle_command(
        DeleteProductGroupCommand(
            user=user,
            organization_id=organization_id,
            group_id=group_id,
        )
    )
