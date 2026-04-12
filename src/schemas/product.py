"""
Pydantic schemas for product API contracts.
"""

from __future__ import annotations

from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import Query
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
    ) -> None:
        self.limit = limit
        self.offset = offset
        self.search_query = search_query
        self.category = category
        self.seller_id = seller_id
        self.include_inactive = include_inactive
        self.sort_by = sort_by
        self.order = order


class ProductListResponse(BaseModel):
    data: list[Product]
    total: int
    limit: int
    offset: int


class ProductCreateRequest(BaseModel):
    title: NonEmptyText
    description: NonEmptyText
    price: NonNegativePrice
    stock: NonNegativeStock
    category: NonEmptyText
    seller_id: UUID = Field(serialization_alias="sellerId")

    @field_validator("seller_id", "price", mode="before")
    @classmethod
    def reject_booleans(cls, v):
        if isinstance(v, bool):
            raise ValueError("Must be a number, not a boolean")
        return v

    @field_validator("title", "description", "category")
    @classmethod
    def reject_empty_strings(cls, v):
        if not v.strip():
            raise ValueError("Must not be empty or blank")
        return v

    @field_validator("category")
    @classmethod
    def normalize_category(cls, value: str) -> str:
        """Store categories in a normalized lowercase form."""
        return value.lower()


class ProductUpdateRequest(BaseModel):
    # TODO
    pass


class ProductStatusUpdateRequest(BaseModel):
    # TODO
    pass
