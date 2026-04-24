"""
Shared enumeration types for the catalog microservice.
"""

from enum import StrEnum


class ProductStatus(StrEnum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    OUT_OF_STOCK = "out_of_stock"


class ProductSortBy(StrEnum):
    PRICE = "price"
    CREATED_AT = "created_at"
    TITLE = "title"


class SortOrder(StrEnum):
    ASC = "asc"
    DESC = "desc"
