"""Service layer exports for the catalog microservice."""

from src.services.product import (
    create_product,
    get_product,
    list_products,
    update_product,
    update_product_status,
)


__all__ = [
    "create_product",
    "get_product",
    "list_products",
    "update_product",
    "update_product_status",
]
