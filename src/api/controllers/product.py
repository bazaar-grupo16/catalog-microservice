"""
Product controller — wires repositories and service, handles request/response mapping.
"""

from __future__ import annotations

from uuid import UUID

from sqlalchemy.orm import Session

from src.dtos import CreateProductDTO, UpdateProductDTO, UpdateProductStatusDTO
from src.repositories import ProductRepository
from src.schemas import (
    ProductCreate,
    ProductListResponse,
    ProductResponse,
    ProductStatusUpdate,
    ProductUpdate,
)
from src.services import ProductService


class ProductController:
    """Instantiates the repository and service, maps HTTP input to DTOs and ORM
    results back to response schemas."""

    def __init__(self, db: Session) -> None:
        self.service = ProductService(
            product_repository=ProductRepository(db),
        )

    async def create_product(self, payload: ProductCreate) -> ProductResponse:
        dto = CreateProductDTO(**payload.model_dump())
        product = self.service.create_product(dto)
        return ProductResponse.model_validate(product)

    async def list_products(
        self,
        *,
        limit: int,
        offset: int,
        search_query: str | None = None,
        category: str | None = None,
        seller_id: UUID | None = None,
        include_inactive: bool = False,
    ) -> ProductListResponse:
        products, total = self.service.list_products(
            limit=limit,
            offset=offset,
            search_query=search_query,
            category=category,
            seller_id=seller_id,
            include_inactive=include_inactive,
        )
        return ProductListResponse(items=products, total=total, limit=limit, offset=offset)

    async def get_product(
        self,
        product_id: UUID,
        *,
        include_inactive: bool = False,
    ) -> ProductResponse:
        product = self.service.get_product(product_id, include_inactive=include_inactive)
        return ProductResponse.model_validate(product)

    async def update_product(
        self,
        product_id: UUID,
        payload: ProductUpdate,
    ) -> ProductResponse:
        dto = UpdateProductDTO(**payload.model_dump())
        product = self.service.update_product(product_id, dto)
        return ProductResponse.model_validate(product)

    async def update_product_status(
        self,
        product_id: UUID,
        payload: ProductStatusUpdate,
    ) -> ProductResponse:
        dto = UpdateProductStatusDTO(**payload.model_dump())
        product = self.service.update_product_status(product_id, dto)
        return ProductResponse.model_validate(product)
