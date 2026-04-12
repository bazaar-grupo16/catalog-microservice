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
    summary="Retrieve a product by ID",
    description="Returns one product details.",
)
async def get_product(
    id: UUID,
    db: DbSession,
) -> ProductResponse:
    return await ProductController(db).get_product(id)


@router.patch(
    "/{id}",
    response_model=ProductResponse,
    summary="Update product",
    description="Partially updates a product. Only the provided fields are modified.",
)
async def update_product(
    id: UUID,
    payload: ProductUpdateRequest,
    db: DbSession,
) -> ProductResponse:
    return await ProductController(db).update_product(id, payload)
