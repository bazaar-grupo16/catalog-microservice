"""
Pydantic schemas for product API contracts.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from src.models import ProductStatus


NonEmptyText = Annotated[str, Field(min_length=1, max_length=150)]
NonNegativePrice = Annotated[Decimal, Field(ge=0, max_digits=10, decimal_places=2)]
NonNegativeStock = Annotated[int, Field(ge=0)]


class ProductBase(BaseModel):
    """Shared writable product fields."""

    title: NonEmptyText
    description: Annotated[str, Field(min_length=1)]
    price: NonNegativePrice
    stock: NonNegativeStock
    category: Annotated[str, Field(min_length=1, max_length=80)]
    seller_id: UUID

    @field_validator("title", "description", "category")
    @classmethod
    def strip_and_validate_text(cls, value: str) -> str:
        """Trim user input and ensure it still contains text."""
        normalized = value.strip()
        if not normalized:
            raise ValueError("must not be blank")
        return normalized

    @field_validator("category")
    @classmethod
    def normalize_category(cls, value: str) -> str:
        """Store categories in a normalized lowercase form."""
        return value.lower()


class ProductCreate(ProductBase):
    """Payload for creating a product."""


class ProductUpdate(ProductBase):
    """Payload for replacing a product."""


class ProductStatusUpdate(BaseModel):
    """Payload for changing publication status."""

    status: ProductStatus


class ProductResponse(BaseModel):
    """Serialized product representation."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    title: str
    description: str
    price: Decimal
    stock: int
    category: str
    seller_id: UUID
    status: ProductStatus
    created_at: datetime
    updated_at: datetime


class ProductListResponse(BaseModel):
    """Paginated collection of products."""

    items: list[ProductResponse]
    total: int
    limit: int
    offset: int
