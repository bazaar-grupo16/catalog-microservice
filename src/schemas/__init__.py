"""API schemas exposed by the catalog service."""

from src.schemas.product import (
    BulkDeleteImageKeysRequest,
    DeleteImagesRequest,
    MyProductsListRequest,
    ProductCreateForm,
    ProductListRequest,
    ProductListResponse,
    ProductResponse,
    ProductUpdateRequest,
    ReorderImagesRequest,
    ShareLinkData,
    ShareLinkResponse,
    StockStatusUpdateRequest,
)
from src.schemas.error import ErrorResponse


__all__ = [
    "ProductCreateForm",
    "MyProductsListRequest",
    "ProductListRequest",
    "ProductListResponse",
    "ProductResponse",
    "ProductUpdateRequest",
    "DeleteImagesRequest",
    "ReorderImagesRequest",
    "BulkDeleteImageKeysRequest",
    "ShareLinkData",
    "ShareLinkResponse",
    "StockStatusUpdateRequest",
    "ErrorResponse",
]
