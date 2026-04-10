"""
Domain exceptions for product operations.
"""

from __future__ import annotations

from uuid import UUID


class ProductNotFound(Exception):
    """Raised when a requested product does not exist or is not visible."""

    def __init__(self, product_id: UUID) -> None:
        self.product_id = product_id
        super().__init__(f"Product {product_id} not found")
