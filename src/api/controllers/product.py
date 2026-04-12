"""
Product controller — wires repositories and service, handles request/response mapping.
"""

from __future__ import annotations

from uuid import UUID

from sqlalchemy.orm import Session

from src.dtos import (
    CreateProductDTO,
    ProductFilterDTO,
    UpdateProductDTO,
    UpdateProductStatusDTO,
)
from src.repositories import ProductRepository
from src.schemas import (
    ProductListRequest,
    ProductListResponse,
    ProductResponse,
    ProductCreateRequest,
    ProductStatusUpdateRequest,
    ProductUpdateRequest,
)
from src.services import ProductService


class ProductController:
    """Instantiates the repository and service, maps HTTP input to DTOs and ORM
    results back to response schemas."""

    def __init__(self, db: Session) -> None:
        self.service = ProductService(
            product_repository=ProductRepository(db),
        )

    async def create_product(self, payload: ProductCreateRequest) -> ProductResponse:
        dto = CreateProductDTO(**payload.model_dump())
        product = self.service.create_product(dto)
        return ProductResponse.model_validate(product)

    async def get_products(self, filters: ProductListRequest) -> ProductListResponse:
        dto = ProductFilterDTO(
            limit=filters.limit,
            offset=filters.offset,
            search_query=filters.search_query,
            category=filters.category,
            seller_id=filters.seller_id,
            include_inactive=filters.include_inactive,
        )
        products, total = self.service.get_products(dto)
        return ProductListResponse(
            data=products, total=total, limit=dto.limit, offset=dto.offset
        )

    async def get_product(
        self,
        product_id: UUID,
        *,
        include_inactive: bool = False,
    ) -> ProductResponse:
        product = self.service.get_product(
            product_id, include_inactive=include_inactive
        )
        return ProductResponse.model_validate(product)

    async def update_product(
        self,
        product_id: UUID,
        payload: ProductUpdateRequest,
    ) -> ProductResponse:
        dto = UpdateProductDTO(**payload.model_dump())
        product = self.service.update_product(product_id, dto)
        return ProductResponse.model_validate(product)

    async def update_product_status(
        self,
        product_id: UUID,
        payload: ProductStatusUpdateRequest,
    ) -> ProductResponse:
        dto = UpdateProductStatusDTO(**payload.model_dump())
        product = self.service.update_product_status(product_id, dto)
        return ProductResponse.model_validate(product)
