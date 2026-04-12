"""
Internal Data Transfer Objects for the catalog microservice.

DTOs carry validated data between the API layer and the service layer.
They have no validation logic — all validation happens in the Pydantic
schemas before the DTO is constructed.
"""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from src.core.enums import ProductStatus


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
    title: str
    description: str
    price: float
    stock: int
    category: str
    seller_id: UUID


@dataclass
class UpdateProductStatusDTO:
    status: ProductStatus


@dataclass
class ProductFilterDTO:
    limit: int
    offset: int
    search_query: str | None = None
    category: str | None = None
    seller_id: UUID | None = None
    include_inactive: bool = False
