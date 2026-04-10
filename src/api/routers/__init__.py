"""Route registrations for the catalog microservice API."""

from src.api.routers.product import router as products_router

__all__ = ["products_router"]
