"""API schemas exposed by the catalog service."""

from src.schemas.product import (
    ProductListRequest,
    ProductListResponse,
    ProductResponse,
    ProductCreateRequest,
    ProductUpdateRequest,
)
from src.schemas.error import ErrorResponse


__all__ = [
    "ProductListRequest",
    "ProductListResponse",
    "ProductResponse",
    "ProductCreateRequest",
    "ProductUpdateRequest",
    "ErrorResponse",
]
