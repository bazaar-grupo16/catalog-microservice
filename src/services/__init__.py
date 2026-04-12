"""Service layer exports for the catalog microservice."""

from src.services.product import ProductService
from src.services.storage import StorageService

__all__ = ["ProductService", "StorageService"]
