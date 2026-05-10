"""
Route registrations for the /my-products endpoint.
"""

from typing import Annotated

from fastapi import APIRouter, Depends

from src.api.controllers import ProductController
from src.core.dependencies import DbSession, UserID
from src.schemas import ErrorResponse, MyProductsFilters, ProductListResponse


router = APIRouter(
    prefix="/my-products",
    tags=["My Products"],
    responses={
        400: {"description": "Bad request error", "model": ErrorResponse},
    },
)


@router.get(
    "",
    summary="Get current user's products",
    response_model=ProductListResponse,
    description=(
        "Returns all products belonging to the seller, "
        "including inactive and out-of-stock listings."
    ),
    responses={
        200: {"description": "A list of the user's products"},
        401: {"description": "Missing or invalid X-User-ID header", "model": ErrorResponse},
    },
)
async def get_my_products(
    db: DbSession,
    user_id: UserID,
    filters: Annotated[MyProductsFilters, Depends()],
) -> ProductListResponse:
    return await ProductController(db).get_my_products(user_id, filters)
