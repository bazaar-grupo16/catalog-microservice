"""
Business logic for product catalog operations.
"""

from __future__ import annotations

from uuid import UUID

from src.dtos import CreateProductDTO, UpdateProductDTO, UpdateProductStatusDTO
from src.exceptions import ProductNotFound
from src.models import Product
from src.repositories import ProductRepository


class ProductService:
    """Service encapsulating business logic for product catalog operations."""

    def __init__(self, product_repository: ProductRepository) -> None:
        self.repository = product_repository

    def create_product(self, dto: CreateProductDTO) -> Product:
        """Create and persist a new product."""
        product = Product(**vars(dto))
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

    def update_product(self, product_id: UUID, dto: UpdateProductDTO) -> Product:
        """Replace product data for an existing product."""
        product = self.repository.find_by_id(product_id, include_inactive=True)
        if product is None:
            raise ProductNotFound(product_id)

        for field, value in vars(dto).items():
            setattr(product, field, value)

        return self.repository.save(product)

    def update_product_status(
        self,
        product_id: UUID,
        dto: UpdateProductStatusDTO,
    ) -> Product:
        """Update the publication status for a product."""
        product = self.repository.find_by_id(product_id, include_inactive=True)
        if product is None:
            raise ProductNotFound(product_id)

        product.status = dto.status.value
        return self.repository.save(product)
