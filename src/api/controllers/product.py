"""
Product controller — wires repositories and service, handles request/response mapping.
"""

from __future__ import annotations

from uuid import UUID

from sqlalchemy.orm import Session

from fastapi import UploadFile

from src.dtos import (
    AddImagesDTO,
    CreateProductDTO,
    DeleteImagesDTO,
    ImageFileDTO,
    ProductFilterDTO,
    ReorderImagesDTO,
    UpdateProductDTO,
)
from src.repositories import ProductRepository
from src.schemas import (
    DeleteImagesRequest,
    ProductCreateForm,
    ProductListRequest,
    ProductListResponse,
    ProductResponse,
    ProductUpdateRequest,
    ReorderImagesRequest,
)
from src.services import ProductService


class ProductController:
    """Instantiates the repository and service, maps HTTP input to DTOs and ORM
    results back to response schemas."""

    def __init__(self, db: Session) -> None:
        self.service = ProductService(
            product_repository=ProductRepository(db),
        )

    async def create_product(
        self, form: ProductCreateForm, files: list[UploadFile]
    ) -> ProductResponse:
        file_dtos = [
            ImageFileDTO(data=await f.read(), content_type=f.content_type or "")
            for f in files
        ]
        dto = CreateProductDTO(
            title=form.title,
            description=form.description,
            price=form.price,
            stock=form.stock,
            category=form.category,
            seller_id=form.seller_id,
        )
        product = self.service.create_product(dto, AddImagesDTO(files=file_dtos))
        return ProductResponse(data=product)

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

    async def get_product(self, product_id: UUID) -> ProductResponse:
        product = self.service.get_product(product_id)
        return ProductResponse(data=product)

    async def delete_product(self, product_id: UUID) -> None:
        self.service.delete_product(product_id)

    async def update_product(
        self,
        product_id: UUID,
        payload: ProductUpdateRequest,
    ) -> ProductResponse:
        dto = UpdateProductDTO(**payload.model_dump())
        product = self.service.update_product(product_id, dto)
        return ProductResponse(data=product)

    async def add_images(
        self, product_id: UUID, files: list[UploadFile]
    ) -> ProductResponse:
        file_dtos = [
            ImageFileDTO(data=await f.read(), content_type=f.content_type or "")
            for f in files
        ]
        product = self.service.add_images(product_id, AddImagesDTO(files=file_dtos))
        return ProductResponse(data=product)

    async def delete_images(
        self, product_id: UUID, payload: DeleteImagesRequest
    ) -> ProductResponse:
        product = self.service.delete_images(
            product_id, DeleteImagesDTO(urls=payload.urls)
        )
        return ProductResponse(data=product)

    async def reorder_images(
        self, product_id: UUID, payload: ReorderImagesRequest
    ) -> ProductResponse:
        product = self.service.reorder_images(
            product_id, ReorderImagesDTO(urls=payload.urls)
        )
        return ProductResponse(data=product)
