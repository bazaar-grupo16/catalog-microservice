"""API routers exposed by the catalog microservice."""

from src.api.health import router as health_router
from src.api.products import router as products_router


__all__ = ["health_router", "products_router"]
