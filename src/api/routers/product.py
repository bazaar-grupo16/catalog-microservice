"""
Product route registrations for the catalog microservice.
"""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, File, Response, UploadFile

from src.api.controllers import ProductController
from src.core.dependencies import DbSession, UserID
from src.schemas import (
    BulkDeleteImageKeysRequest,
    DeleteImagesRequest,
    ErrorResponse,
    ProductCreateForm,
    ProductListRequest,
    ProductListResponse,
    ProductResponse,
    ProductUpdateRequest,
    ReorderImagesRequest,
    ShareLinkResponse,
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
        "Requires at least one image (JPEG, PNG or WebP; max 10 MB each). "
        "The seller is identified by the X-User-ID header."
    ),
    responses={
        201: {"description": "Product created successfully"},
        400: {"description": "Image validation failed", "model": ErrorResponse},
        401: {"description": "Missing or invalid X-User-ID header", "model": ErrorResponse},
    },
)
async def create_product(
    db: DbSession,
    user_id: UserID,
    form: Annotated[ProductCreateForm, Depends()],
    files: Annotated[
        list[UploadFile],
        File(description="Product images (JPEG, PNG or WebP; max 10 MB each)"),
    ],
) -> ProductResponse:
    return await ProductController(db).create_product(form, files, user_id)


@router.get(
    "",
    summary="Retrieve all products",
    response_model=ProductListResponse,
    responses={200: {"description": "A list of products"}},
    description=(
        "Lists products using catalog visibility rules by default. "
        "Only products currently visible in the catalog are returned unless "
        "include_inactive=true."
    ),
)
async def get_products(
    db: DbSession,
    filters: Annotated[ProductListRequest, Depends()],
) -> ProductListResponse:
    return await ProductController(db).get_products(filters)



@router.get(
    "/{id}/share-link",
    response_model=ShareLinkResponse,
    summary="Get a shareable link for a product",
    description="Returns a public URL that links directly to the product detail.",
    responses={
        404: {"description": "Product not found or not available", "model": ErrorResponse},
    },
)
async def get_product_share_link(
    id: UUID,
    db: DbSession,
) -> ShareLinkResponse:
    return await ProductController(db).get_share_link(id)


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


@router.delete(
    "/{id}",
    status_code=204,
    summary="Delete a product by ID",
    description=(
        "Deletes the product and attempts to remove all its images from storage. "
        "Storage errors are logged as warnings and do not abort the deletion."
    ),
    responses={
        204: {"description": "Product deleted successfully"},
        401: {"description": "Missing or invalid X-User-ID header", "model": ErrorResponse},
        404: {"description": "Product not found", "model": ErrorResponse},
    },
)
async def delete_product(
    id: UUID,
    db: DbSession,
    user_id: UserID,
) -> Response:
    await ProductController(db).delete_product(id)
    return Response(status_code=204)


@router.patch(
    "/{id}",
    response_model=ProductResponse,
    summary="Update product",
    description="Partially updates a product. Only the provided fields are modified.",
    responses={
        401: {"description": "Missing or invalid X-User-ID header", "model": ErrorResponse},
    },
)
async def update_product(
    id: UUID,
    payload: ProductUpdateRequest,
    db: DbSession,
    user_id: UserID,
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
        401: {"description": "Missing or invalid X-User-ID header", "model": ErrorResponse},
        404: {"description": "Product not found", "model": ErrorResponse},
    },
)
async def add_images(
    id: UUID,
    db: DbSession,
    user_id: UserID,
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
        "Products cannot be left with zero images."
    ),
    responses={
        200: {"description": "Images deleted and product returned"},
        400: {
            "description": "One or more URLs not found in product",
            "model": ErrorResponse,
        },
        401: {"description": "Missing or invalid X-User-ID header", "model": ErrorResponse},
        404: {"description": "Product not found", "model": ErrorResponse},
        409: {
            "description": "Would leave product with no images",
            "model": ErrorResponse,
        },
    },
)
async def delete_images(
    id: UUID,
    payload: DeleteImagesRequest,
    db: DbSession,
    user_id: UserID,
) -> ProductResponse:
    return await ProductController(db).delete_images(id, payload)


@router.delete(
    "/{product_id}/images/bulk",
    response_model=ProductResponse,
    summary="Bulk delete product images by key",
    description=(
        "Deletes one or more images by storage key from the product and from storage. "
        "All keys must belong to the product. "
        "Products cannot be left with zero images."
    ),
    responses={
        200: {"description": "Images deleted and product returned"},
        401: {"description": "Missing or invalid X-User-ID header", "model": ErrorResponse},
        404: {
            "description": "Product or one or more image keys not found",
            "model": ErrorResponse,
        },
        409: {
            "description": "Would leave product with no images",
            "model": ErrorResponse,
        },
    },
)
async def bulk_delete_images(
    product_id: UUID,
    payload: BulkDeleteImageKeysRequest,
    db: DbSession,
    user_id: UserID,
) -> ProductResponse:
    return await ProductController(db).bulk_delete_images_by_keys(product_id, payload)


@router.delete(
    "/{product_id}/images/{image_key}",
    response_model=ProductResponse,
    summary="Delete a product image by key",
    description=(
        "Deletes a single image identified by its storage key (filename in the bucket) "
        "from the product and from storage. "
        "Products cannot be left with zero images."
    ),
    responses={
        200: {"description": "Image deleted and product returned"},
        401: {"description": "Missing or invalid X-User-ID header", "model": ErrorResponse},
        404: {
            "description": "Product or image key not found",
            "model": ErrorResponse,
        },
        409: {
            "description": "Would leave product with no images",
            "model": ErrorResponse,
        },
    },
)
async def delete_image_by_key(
    product_id: UUID,
    image_key: str,
    db: DbSession,
    user_id: UserID,
) -> ProductResponse:
    return await ProductController(db).delete_image_by_key(product_id, image_key)


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
        401: {"description": "Missing or invalid X-User-ID header", "model": ErrorResponse},
        404: {"description": "Product not found", "model": ErrorResponse},
    },
)
async def reorder_images(
    id: UUID,
    payload: ReorderImagesRequest,
    db: DbSession,
    user_id: UserID,
) -> ProductResponse:
    return await ProductController(db).reorder_images(id, payload)

@router.patch(
    "/{id}/block",
    response_model=ProductResponse,
    summary="Block a product",
    description="Admin only: disables a product from public view.",
    responses={
        401: {"description": "Missing or invalid X-User-ID header", "model": ErrorResponse},
        404: {"description": "Product not found", "model": ErrorResponse},
    },
)
async def block_product(
    id: UUID,
    db: DbSession,
    user_id: UserID,
) -> ProductResponse:
    return await ProductController(db).block_product(id, user_id)


@router.patch(
    "/{id}/unblock",
    response_model=ProductResponse,
    summary="Unblock a product",
    description="Admin only: reinstates a previously blocked product.",
    responses={
        401: {"description": "Missing or invalid X-User-ID header", "model": ErrorResponse},
        404: {"description": "Product not found", "model": ErrorResponse},
    },
)
async def unblock_product(
    id: UUID,
    db: DbSession,
    user_id: UserID,
) -> ProductResponse:
    return await ProductController(db).unblock_product(id, user_id)