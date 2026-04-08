"""API schemas exposed by the catalog service."""

from src.schemas.product import (
    ProductCreate,
    ProductListResponse,
    ProductResponse,
    ProductStatusUpdate,
    ProductUpdate,
)


__all__ = [
    "ProductCreate",
    "ProductListResponse",
    "ProductResponse",
    "ProductStatusUpdate",
    "ProductUpdate",
]
