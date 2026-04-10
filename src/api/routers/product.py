"""
Product route registrations for the catalog microservice.
"""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Query, status

from src.api.controllers import ProductController
from src.core.dependencies import DbSession
from src.schemas import (
    ProductCreate,
    ProductListResponse,
    ProductResponse,
    ProductStatusUpdate,
    ProductUpdate,
)


router = APIRouter(prefix="/products", tags=["Products"])


@router.post(
    "",
    response_model=ProductResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create product",
    description="Creates a new product publication in the catalog.",
)
async def create_product_endpoint(
    payload: ProductCreate,
    db: DbSession,
) -> ProductResponse:
    return await ProductController(db).create_product(payload)


@router.get(
    "",
    response_model=ProductListResponse,
    summary="List products",
    description=(
        "Lists products using catalog visibility rules by default. "
        "Only active products with stock are returned unless include_inactive=true."
    ),
)
async def list_products_endpoint(
    db: DbSession,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
    search_query: str | None = Query(default=None, min_length=1),
    category: str | None = Query(default=None, min_length=1, max_length=80),
    seller_id: UUID | None = None,
    include_inactive: bool = False,
) -> ProductListResponse:
    return await ProductController(db).list_products(
        limit=limit,
        offset=offset,
        search_query=search_query,
        category=category,
        seller_id=seller_id,
        include_inactive=include_inactive,
    )


@router.get(
    "/{product_id}",
    response_model=ProductResponse,
    summary="Get product detail",
    description=(
        "Returns one product. Inactive products are hidden by default and return 404 "
        "unless include_inactive=true is provided."
    ),
)
async def get_product_endpoint(
    product_id: UUID,
    db: DbSession,
    include_inactive: bool = False,
) -> ProductResponse:
    return await ProductController(db).get_product(product_id, include_inactive=include_inactive)


@router.put(
    "/{product_id}",
    response_model=ProductResponse,
    summary="Replace product",
    description="Replaces the editable fields of an existing product.",
)
async def update_product_endpoint(
    product_id: UUID,
    payload: ProductUpdate,
    db: DbSession,
) -> ProductResponse:
    return await ProductController(db).update_product(product_id, payload)


@router.patch(
    "/{product_id}/status",
    response_model=ProductResponse,
    summary="Change product status",
    description="Publishes or unpublishes a product by updating its status.",
)
async def update_product_status_endpoint(
    product_id: UUID,
    payload: ProductStatusUpdate,
    db: DbSession,
) -> ProductResponse:
    return await ProductController(db).update_product_status(product_id, payload)
