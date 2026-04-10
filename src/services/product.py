"""
Business logic for product catalog operations.
"""

from __future__ import annotations

from uuid import UUID

from sqlalchemy.orm import Session

from src.exceptions import ProductNotFound
from src.models import Product
from src.repositories import ProductRepository
from src.schemas import ProductCreate, ProductStatusUpdate, ProductUpdate


class ProductService:
    """Service encapsulating business logic for product catalog operations."""

    def __init__(self, db: Session) -> None:
        self.repository = ProductRepository(db)

    def create_product(self, payload: ProductCreate) -> Product:
        """Create and persist a new product."""
        product = Product(**payload.model_dump())
        return self.repository.create(product)

    def list_products(
        self,
        *,
        limit: int,
        offset: int,
        search_query: str | None = None,
        category: str | None = None,
        seller_id: UUID | None = None,
        include_inactive: bool = False,
    ) -> tuple[list[Product], int]:
        """Return a paginated product list following public visibility rules."""
        return self.repository.find_all(
            limit=limit,
            offset=offset,
            search_query=search_query,
            category=category,
            seller_id=seller_id,
            include_inactive=include_inactive,
        )

    def get_product(
        self,
        product_id: UUID,
        *,
        include_inactive: bool = False,
    ) -> Product:
        """Fetch a single product, optionally including inactive ones."""
        product = self.repository.find_by_id(product_id, include_inactive=include_inactive)
        if product is None:
            raise ProductNotFound(product_id)
        return product

    def update_product(self, product_id: UUID, payload: ProductUpdate) -> Product:
        """Replace product data for an existing product."""
        product = self.repository.find_by_id(product_id, include_inactive=True)
        if product is None:
            raise ProductNotFound(product_id)

        for field, value in payload.model_dump().items():
            setattr(product, field, value)

        return self.repository.save(product)

    def update_product_status(
        self,
        product_id: UUID,
        payload: ProductStatusUpdate,
    ) -> Product:
        """Update the publication status for a product."""
        product = self.repository.find_by_id(product_id, include_inactive=True)
        if product is None:
            raise ProductNotFound(product_id)

        product.status = payload.status.value
        return self.repository.save(product)
