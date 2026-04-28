"""Domain exception types for the catalog microservice."""

from src.exceptions.product import (
    EmptyActiveProductImages,
    ImageNotFound,
    ImageValidationError,
    InvalidImageURLs,
    ProductNotAvailable,
    ProductNotFound,
)

__all__ = [
    "ProductNotFound",
    "ProductNotAvailable",
    "ImageValidationError",
    "InvalidImageURLs",
    "EmptyActiveProductImages",
    "ImageNotFound",
]
