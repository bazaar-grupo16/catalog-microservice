"""
Product CRUD endpoints for the catalog microservice.
"""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status

from src.core.dependencies import DbSession
from src.schemas import (
    ProductCreate,
    ProductListResponse,
    ProductResponse,
    ProductStatusUpdate,
    ProductUpdate,
)
from src.services import (
    create_product,
    get_product,
    list_products,
    update_product,
    update_product_status,
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
    return create_product(db, payload)


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
    category: str | None = Query(default=None, min_length=1, max_length=80),
    seller_id: UUID | None = None,
    include_inactive: bool = False,
) -> ProductListResponse:
    products, total = list_products(
        db,
        limit=limit,
        offset=offset,
        category=category,
        seller_id=seller_id,
        include_inactive=include_inactive,
    )
    return ProductListResponse(items=products, total=total, limit=limit, offset=offset)


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
    product = get_product(db, product_id, include_inactive=include_inactive)
    if product is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found",
        )
    return product


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
    product = update_product(db, product_id, payload)
    if product is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found",
        )
    return product


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
    product = update_product_status(db, product_id, payload)
    if product is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found",
        )
    return product
