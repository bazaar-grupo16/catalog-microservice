"""API schemas exposed by the catalog service."""

from src.schemas.product import (
    BulkDeleteImageKeysRequest,
    DeleteImagesRequest,
    MyProductsFilters,
    ProductCreateForm,
    ProductListRequest,
    ProductListResponse,
    ProductResponse,
    ProductStatusHistoryEntry,
    ProductStatusHistoryResponse,
    ProductUpdateRequest,
    ReorderImagesRequest,
    ShareLinkData,
    ShareLinkResponse,
    StockStatusUpdateRequest,
)
from src.schemas.error import ErrorResponse


__all__ = [
    "ProductCreateForm",
    "MyProductsFilters",
    "ProductListRequest",
    "ProductListResponse",
    "ProductResponse",
    "ProductStatusHistoryEntry",
    "ProductStatusHistoryResponse",
    "ProductUpdateRequest",
    "DeleteImagesRequest",
    "ReorderImagesRequest",
    "BulkDeleteImageKeysRequest",
    "ShareLinkData",
    "ShareLinkResponse",
    "StockStatusUpdateRequest",
    "ErrorResponse",
]
