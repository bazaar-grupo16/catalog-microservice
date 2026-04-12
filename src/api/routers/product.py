"""
Product route registrations for the catalog microservice.
"""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, File, UploadFile

from src.api.controllers import ProductController
from src.core.dependencies import DbSession
from src.schemas import (
    DeleteImagesRequest,
    ProductCreateForm,
    ProductListRequest,
    ProductListResponse,
    ProductResponse,
    ProductUpdateRequest,
    ReorderImagesRequest,
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
    description=(
        "Creates a new product publication in the catalog. "
        "Requires at least one image (JPEG, PNG or WebP; max 10 MB each)."
    ),
    responses={
        201: {"description": "Product created successfully"},
        400: {"description": "Image validation failed", "model": ErrorResponse},
    },
)
async def create_product(
    db: DbSession,
    form: Annotated[ProductCreateForm, Depends()],
    files: Annotated[
        list[UploadFile],
        File(description="Product images (JPEG, PNG or WebP; max 10 MB each)"),
    ],
) -> ProductResponse:
    return await ProductController(db).create_product(form, files)


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


@router.post(
    "/{id}/images",
    response_model=ProductResponse,
    summary="Upload product images",
    description=(
        "Accepts one or more image files (JPEG, PNG or WebP; max 10 MB each) and "
        "appends their CDN URLs to the product's images array. "
        "The entire request is rejected if any file fails validation."
    ),
    responses={
        200: {"description": "Images uploaded and product returned"},
        400: {"description": "File validation failed", "model": ErrorResponse},
        404: {"description": "Product not found", "model": ErrorResponse},
    },
)
async def add_images(
    id: UUID,
    db: DbSession,
    files: Annotated[list[UploadFile], File(description="Image files to upload")],
) -> ProductResponse:
    return await ProductController(db).add_images(id, files)


@router.delete(
    "/{id}/images",
    response_model=ProductResponse,
    summary="Delete product images",
    description=(
        "Deletes one or more images by URL from the product and from storage. "
        "All URLs must belong to the product. "
        "Active products cannot be left with zero images."
    ),
    responses={
        200: {"description": "Images deleted and product returned"},
        400: {
            "description": "One or more URLs not found in product",
            "model": ErrorResponse,
        },
        404: {"description": "Product not found", "model": ErrorResponse},
        409: {
            "description": "Would leave active product with no images",
            "model": ErrorResponse,
        },
    },
)
async def delete_images(
    id: UUID,
    payload: DeleteImagesRequest,
    db: DbSession,
) -> ProductResponse:
    return await ProductController(db).delete_images(id, payload)


@router.patch(
    "/{id}/images/order",
    response_model=ProductResponse,
    summary="Reorder product images",
    description=(
        "Replaces the images array with a new ordering of the same URLs. "
        "The request must contain exactly the same URLs as the current array — "
        "no missing, no extra, no duplicates."
    ),
    responses={
        200: {"description": "Images reordered and product returned"},
        400: {
            "description": "URL set does not match current images",
            "model": ErrorResponse,
        },
        404: {"description": "Product not found", "model": ErrorResponse},
    },
)
async def reorder_images(
    id: UUID,
    payload: ReorderImagesRequest,
    db: DbSession,
) -> ProductResponse:
    return await ProductController(db).reorder_images(id, payload)
