"""
Product route registrations for the catalog microservice.
"""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends

from src.api.controllers import ProductController
from src.core.dependencies import DbSession
from src.schemas import (
    ProductCreateRequest,
    ProductListRequest,
    ProductListResponse,
    ProductResponse,
    ProductStatusUpdateRequest,
    ProductUpdateRequest,
    ErrorResponse,
)


router = APIRouter(
    prefix="/products",
    tags=["Products"],
    responses={
        400: {"description": "Bad request error", "model": ErrorResponse},
    },
)


@router.post(
    "",
    status_code=201,
    summary="Create a new product",
    response_model=ProductResponse,
    description="Creates a new product publication in the catalog.",
    responses={
        201: {"description": "Product created successfully"},
    },
)
async def create_product(
    payload: ProductCreateRequest,
    db: DbSession,
) -> ProductResponse:
    return await ProductController(db).create_product(payload)


@router.get(
    "",
    summary="Retrieve all products",
    response_model=ProductListResponse,
    responses={200: {"description": "A list of products"}},
    description=(
        "Lists products using catalog visibility rules by default. "
        "Only active products with stock are returned unless include_inactive=true."
    ),
)
async def get_products(
    db: DbSession,
    filters: Annotated[ProductListRequest, Depends()],
) -> ProductListResponse:
    return await ProductController(db).get_products(filters)


@router.get(
    "/{id}",
    response_model=ProductResponse,
    summary="Get product detail",
    description=(
        "Returns one product. Inactive products are hidden by default and return 404 "
        "unless include_inactive=true is provided."
    ),
)
async def get_product(
    id: UUID,
    db: DbSession,
    include_inactive: bool = False,
) -> ProductResponse:
    return await ProductController(db).get_product(
        id, include_inactive=include_inactive
    )


@router.put(
    "/{product_id}",
    response_model=ProductResponse,
    summary="Replace product",
    description="Replaces the editable fields of an existing product.",
)
async def update_product_endpoint(
    product_id: UUID,
    payload: ProductUpdateRequest,
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
    payload: ProductStatusUpdateRequest,
    db: DbSession,
) -> ProductResponse:
    return await ProductController(db).update_product_status(product_id, payload)
