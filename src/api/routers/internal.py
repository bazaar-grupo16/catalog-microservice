"""
Internal route registrations — only accessible within the Kubernetes cluster.
Not exposed through the Nginx Ingress.
"""

from uuid import UUID

from fastapi import APIRouter

from src.api.controllers import InternalController
from src.core.dependencies import DbSession
from src.schemas import ErrorResponse, ProductResponse, StockStatusUpdateRequest


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
