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


class ProductNotAvailable(Exception):
    """Raised when a product exists but has been disabled (inactive status)."""

    def __init__(self, product_id: UUID) -> None:
        self.product_id = product_id
        super().__init__(f"Product {product_id} not available")


class ImageValidationError(Exception):
    """Raised when an uploaded image file fails MIME-type or size validation."""

    def __init__(self, detail: str) -> None:
        self.detail = detail
        super().__init__(detail)


class InvalidImageURLs(Exception):
    """Raised when the caller references URLs not present in the product's images array."""

    def __init__(self, urls: list[str]) -> None:
        self.urls = urls
        super().__init__(f"Image URLs not found in product: {urls}")


class EmptyActiveProductImages(Exception):
    """Raised when an operation would leave a product with zero images."""


class ImageNotFound(Exception):
    """Raised when one or more image keys are not found in the product's images array."""

    def __init__(self, keys: list[str]) -> None:
        self.keys = keys
        super().__init__(f"Image keys not found in product: {keys}")
