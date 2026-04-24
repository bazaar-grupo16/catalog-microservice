"""Controller layer for the catalog microservice API."""

from src.api.controllers.product import ProductController
from src.api.controllers.internal import InternalController

__all__ = ["ProductController", "InternalController"]
