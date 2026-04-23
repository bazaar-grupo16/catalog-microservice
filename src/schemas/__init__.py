"""API schemas exposed by the catalog service."""

from src.schemas.product import (
    BulkDeleteImageKeysRequest,
    DeleteImagesRequest,
    ProductCreateForm,
    ProductListRequest,
    ProductListResponse,
    ProductResponse,
    ProductUpdateRequest,
    ReorderImagesRequest,
)
from src.schemas.error import ErrorResponse


__all__ = [
    "ProductCreateForm",
    "ProductListRequest",
    "ProductListResponse",
    "ProductResponse",
    "ProductUpdateRequest",
    "DeleteImagesRequest",
    "ReorderImagesRequest",
    "BulkDeleteImageKeysRequest",
    "ErrorResponse",
]
