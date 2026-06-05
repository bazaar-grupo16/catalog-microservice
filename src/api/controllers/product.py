"""
Product controller — wires repositories and service, handles request/response mapping.
"""

from __future__ import annotations

from uuid import UUID

from sqlalchemy.orm import Session

from fastapi import UploadFile

from src.dtos import (
    AddImagesDTO,
    BulkDeleteImagesByKeysDTO,
    CreateProductDTO,
    DeleteImageByKeyDTO,
    DeleteImagesDTO,
    ImageFileDTO,
    ProductFilterDTO,
    ReorderImagesDTO,
    UpdateProductDTO,
)
from src.repositories import ProductRepository, ProductStatusHistoryRepository
from src.services.inventory import InventoryService
from src.services.storage import StorageService
from src.schemas import (
    BulkDeleteImageKeysRequest,
    DeleteImagesRequest,
    MyProductsFilters,
    ProductCreateForm,
    ProductListRequest,
    ProductListResponse,
    ProductResponse,
    ProductStatusHistoryResponse,
    ProductUpdateRequest,
    ReorderImagesRequest,
    ShareLinkData,
    ShareLinkResponse,
)
from src.services import ProductService


class ProductController:
    """Instantiates the repository and service, maps HTTP input to DTOs and ORM
    results back to response schemas."""

    def __init__(self, db: Session) -> None:
        self.service = ProductService(
            product_repository=ProductRepository(db),
            storage_service=StorageService(),
            inventory_service=InventoryService(),
            history_repository=ProductStatusHistoryRepository(db),
        )

    async def create_product(
        self, form: ProductCreateForm, files: list[UploadFile], seller_id: UUID
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
            seller_id=seller_id,
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
            include_blocked=filters.include_blocked,
            sort_by=filters.sort_by,
            order=filters.order,
            min_price=filters.min_price,
            max_price=filters.max_price,
        )
        products, total = self.service.get_products(dto)
        return ProductListResponse(
            data=products, total=total, limit=dto.limit, offset=dto.offset
        )

    async def get_my_products(
        self, user_id: UUID, filters: MyProductsFilters
    ) -> ProductListResponse:
        dto = ProductFilterDTO(
            limit=filters.limit,
            offset=filters.offset,
            search_query=filters.search_query,
            sort_by=filters.sort_by,
            order=filters.order,
            seller_id=user_id,
            include_inactive=True,
        )
        products, total = self.service.get_products(dto)
        return ProductListResponse(
            data=products, total=total, limit=dto.limit, offset=dto.offset
        )

    async def get_product(self, product_id: UUID) -> ProductResponse:
        product = self.service.get_product(product_id)
        return ProductResponse(data=product)

    async def get_share_link(self, product_id: UUID) -> ShareLinkResponse:
        url = self.service.get_share_link(product_id)
        return ShareLinkResponse(data=ShareLinkData(product_id=product_id, url=url))

    async def delete_product(self, product_id: UUID) -> None:
        self.service.delete_product(product_id)

    async def update_product(
        self,
        product_id: UUID,
        payload: ProductUpdateRequest,
        user_id: UUID,
    ) -> ProductResponse:
        dto = UpdateProductDTO(**payload.model_dump())
        product = self.service.update_product(product_id, dto, changed_by=user_id)
        return ProductResponse(data=product)

    async def get_status_history(self, product_id: UUID) -> ProductStatusHistoryResponse:
        entries = self.service.get_status_history(product_id)
        return ProductStatusHistoryResponse(data=entries)

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

    async def delete_image_by_key(
        self, product_id: UUID, image_key: str
    ) -> ProductResponse:
        product = self.service.delete_image_by_key(
            product_id, DeleteImageByKeyDTO(image_key=image_key)
        )
        return ProductResponse(data=product)

    async def bulk_delete_images_by_keys(
        self, product_id: UUID, payload: BulkDeleteImageKeysRequest
    ) -> ProductResponse:
        product = self.service.bulk_delete_images_by_keys(
            product_id, BulkDeleteImagesByKeysDTO(image_keys=payload.image_keys)
        )
        return ProductResponse(data=product)
    
    async def block_product(self, product_id: UUID, user_id: UUID) -> ProductResponse:
        product = self.service.block_product(product_id, user_id)
        return ProductResponse(data=product)

    async def unblock_product(self, product_id: UUID, user_id: UUID) -> ProductResponse:
        product = self.service.unblock_product(product_id, user_id)
        return ProductResponse(data=product)
