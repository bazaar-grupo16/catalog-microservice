"""
Business logic for product catalog operations.
"""

from __future__ import annotations

from uuid import UUID

from sqlalchemy.orm import Session

from src.models import Product
from src.repositories import ProductRepository
from src.schemas import ProductCreate, ProductStatusUpdate, ProductUpdate


def create_product(db: Session, payload: ProductCreate) -> Product:
    """Create and persist a new product."""
    product = Product(**payload.model_dump())
    return ProductRepository.create(db, product)


def list_products(
    db: Session,
    *,
    limit: int,
    offset: int,
    search_query: str | None = None,
    category: str | None = None,
    seller_id: UUID | None = None,
    include_inactive: bool = False,
) -> tuple[list[Product], int]:
    """Return a paginated product list following public visibility rules."""
    return ProductRepository.find_all(
        db,
        limit=limit,
        offset=offset,
        search_query=search_query,
        category=category,
        seller_id=seller_id,
        include_inactive=include_inactive,
    )


def get_product(
    db: Session,
    product_id: UUID,
    *,
    include_inactive: bool = False,
) -> Product | None:
    """Fetch a single product, optionally including inactive ones."""
    return ProductRepository.find_by_id(db, product_id, include_inactive=include_inactive)


def update_product(db: Session, product_id: UUID, payload: ProductUpdate) -> Product | None:
    """Replace product data for an existing product."""
    product = ProductRepository.find_by_id(db, product_id, include_inactive=True)
    if product is None:
        return None

    for field, value in payload.model_dump().items():
        setattr(product, field, value)

    return ProductRepository.save(db, product)


def update_product_status(
    db: Session,
    product_id: UUID,
    payload: ProductStatusUpdate,
) -> Product | None:
    """Update the publication status for a product."""
    product = ProductRepository.find_by_id(db, product_id, include_inactive=True)
    if product is None:
        return None

    product.status = payload.status.value
    return ProductRepository.save(db, product)
