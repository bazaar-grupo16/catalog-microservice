"""
Internal Data Transfer Objects for the catalog microservice.

DTOs carry validated data between the API layer and the service layer.
They have no validation logic — all validation happens in the Pydantic
schemas before the DTO is constructed.
"""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from src.core.enums import ProductSortBy, ProductStatus, SortOrder


@dataclass
class CreateProductDTO:
    title: str
    description: str
    price: float
    stock: int
    category: str
    seller_id: UUID


@dataclass
class UpdateProductDTO:
    title: str | None = None
    description: str | None = None
    price: float | None = None
    stock: int | None = None
    category: str | None = None
    status: ProductStatus | None = None


@dataclass
class ProductFilterDTO:
    limit: int
    offset: int
    search_query: str | None = None
    category: str | None = None
    seller_id: UUID | None = None
    include_inactive: bool = False
    sort_by: ProductSortBy | None = None
    order: SortOrder = SortOrder.ASC
    min_price: float | None = None
    max_price: float | None = None


@dataclass
class ImageFileDTO:
    data: bytes
    content_type: str


@dataclass
class AddImagesDTO:
    files: list[ImageFileDTO]


@dataclass
class DeleteImagesDTO:
    urls: list[str]


@dataclass
class ReorderImagesDTO:
    urls: list[str]


@dataclass
class DeleteImageByKeyDTO:
    image_key: str


@dataclass
class BulkDeleteImagesByKeysDTO:
    image_keys: list[str]
