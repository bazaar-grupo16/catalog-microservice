"""
Internal route registrations — only accessible within the Kubernetes cluster.
Not exposed through the Nginx Ingress.
"""

from uuid import UUID

from fastapi import APIRouter

from src.api.controllers import InternalController
from src.core.dependencies import DbSession
from src.schemas import ErrorResponse, ProductResponse, SellerBlockRequest, SellerBlockResponse, StockStatusUpdateRequest


router = APIRouter(prefix="/internal", tags=["Internal"])


@router.patch(
    "/products/{product_id}/stock-status",
    response_model=ProductResponse,
    summary="Update product stock status",
    description=(
        "Called by the inventory service when a product's stock reaches zero or is replenished. "
        "Transitions active products to out_of_stock and vice versa. "
        "Inactive products are unaffected."
    ),
    responses={
        200: {"description": "Status updated, product returned"},
        404: {"description": "Product not found", "model": ErrorResponse},
    },
)
async def update_stock_status(
    product_id: UUID,
    payload: StockStatusUpdateRequest,
    db: DbSession,
) -> ProductResponse:
    return await InternalController(db).update_stock_status(product_id, payload)


@router.patch(
    "/sellers/{seller_id}/block",
    response_model=SellerBlockResponse,
    summary="Block all products of a seller",
    description=(
        "Called by the backoffice when an admin blocks a user. "
        "Sets is_blocked=True on every product belonging to the given seller_id."
    ),
    responses={
        200: {"description": "Products blocked, count of affected products returned"},
    },
)
async def block_seller_products(
    seller_id: UUID,
    payload: SellerBlockRequest,
    db: DbSession,
) -> SellerBlockResponse:
    return await InternalController(db).block_seller_products(seller_id, payload)


@router.patch(
    "/sellers/{seller_id}/unblock",
    response_model=SellerBlockResponse,
    summary="Unblock all products of a seller",
    description=(
        "Called by the backoffice when an admin unblocks a user. "
        "Sets is_blocked=False on every product belonging to the given seller_id."
    ),
    responses={
        200: {"description": "Products unblocked, count of affected products returned"},
    },
)
async def unblock_seller_products(
    seller_id: UUID,
    payload: SellerBlockRequest,
    db: DbSession,
) -> SellerBlockResponse:
    return await InternalController(db).unblock_seller_products(seller_id, payload)
