"""
Pydantic schemas for product API contracts.
"""

from __future__ import annotations

from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import Form, HTTPException, Query
from pydantic import BaseModel, ConfigDict, Field, field_validator

from src.core.enums import ProductSortBy, ProductStatus, SortOrder


NonEmptyText = Annotated[str, Field(min_length=1, max_length=150)]
NonNegativePrice = Annotated[float, Field(ge=0.01)]
NonNegativeStock = Annotated[int, Field(ge=0)]


class Product(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    title: NonEmptyText
    description: NonEmptyText
    price: NonNegativePrice
    stock: NonNegativeStock
    category: NonEmptyText
    seller_id: UUID = Field(serialization_alias="sellerId")
    status: ProductStatus
    created_at: datetime = Field(serialization_alias="createdAt")
    updated_at: datetime = Field(serialization_alias="updatedAt")
    images: list[str] = []


class ProductResponse(BaseModel):
    data: Product


class ProductListRequest:
    def __init__(
        self,
        limit: Annotated[int, Query(ge=1, le=50)] = 20,
        offset: Annotated[int, Query(ge=0)] = 0,
        search_query: str | None = Query(default=None, min_length=1),
        category: str | None = Query(default=None, min_length=1, max_length=150),
        seller_id: UUID | None = None,
        include_inactive: bool = False,
        sort_by: ProductSortBy | None = None,
        order: SortOrder = SortOrder.ASC,
        min_price: float | None = Query(default=None, gt=0),
        max_price: float | None = Query(default=None, gt=0),
    ) -> None:
        self.limit = limit
        self.offset = offset
        self.search_query = search_query
        self.category = category
        self.seller_id = seller_id
        self.include_inactive = include_inactive
        self.sort_by = sort_by
        self.order = order
        self.min_price = min_price
        self.max_price = max_price


class ProductListResponse(BaseModel):
    data: list[Product]
    total: int
    limit: int
    offset: int


class ProductUpdateRequest(BaseModel):
    title: NonEmptyText | None = None
    description: NonEmptyText | None = None
    price: NonNegativePrice | None = None
    stock: NonNegativeStock | None = None
    category: NonEmptyText | None = None
    status: ProductStatus | None = None

    @field_validator("price", mode="before")
    @classmethod
    def reject_booleans(cls, v):
        if isinstance(v, bool):
            raise ValueError("Must be a number, not a boolean")
        return v

    @field_validator("title", "description", "category")
    @classmethod
    def reject_empty_strings(cls, v):
        if v is not None and not v.strip():
            raise ValueError("Must not be empty or blank")
        return v

    @field_validator("category")
    @classmethod
    def normalize_category(cls, value: str | None) -> str | None:
        return value.lower() if value is not None else None


class ProductCreateForm:
    """Multipart form dependency for product creation.

    Follows the same ``__init__``-based pattern as ``ProductListRequest``
    so FastAPI injects it via ``Depends()``.  Validates and normalises
    the incoming form fields before they reach the controller.
    """

    def __init__(
        self,
        title: Annotated[str, Form(min_length=1, max_length=150)],
        description: Annotated[str, Form(min_length=1)],
        price: Annotated[float, Form(ge=0.01)],
        stock: Annotated[int, Form(ge=0)],
        category: Annotated[str, Form(min_length=1, max_length=80)],
        seller_id: Annotated[UUID, Form()],
    ) -> None:
        for field, value in [
            ("title", title),
            ("description", description),
            ("category", category),
        ]:
            if not value.strip():
                raise HTTPException(
                    status_code=422,
                    detail=f"{field} must not be blank",
                )
        self.title = title
        self.description = description
        self.price = price
        self.stock = stock
        self.category = category.strip().lower()
        self.seller_id = seller_id


class DeleteImagesRequest(BaseModel):
    urls: list[str] = Field(min_length=1)


class ReorderImagesRequest(BaseModel):
    urls: list[str] = Field(min_length=1)


class BulkDeleteImageKeysRequest(BaseModel):
    image_keys: list[str] = Field(min_length=1)


class StockStatusUpdateRequest(BaseModel):
    has_stock: bool
