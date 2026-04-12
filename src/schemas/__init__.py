"""API schemas exposed by the catalog service."""

from src.schemas.product import (
    ProductListResponse,
    ProductResponse,
    ProductCreateRequest,
    ProductStatusUpdateRequest,
    ProductUpdateRequest,
)
from src.schemas.error import ErrorResponse


__all__ = [
    "ProductListResponse",
    "ProductResponse",
    "ProductCreateRequest",
    "ProductStatusUpdateRequest",
    "ProductUpdateRequest",
    "ErrorResponse",
]
