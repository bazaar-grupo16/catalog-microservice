"""
Business logic for product catalog operations.
"""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import case, func, or_, select
from sqlalchemy.orm import Session

from src.models import Product, ProductStatus
from src.schemas import ProductCreate, ProductStatusUpdate, ProductUpdate


def create_product(db: Session, payload: ProductCreate) -> Product:
    """Create and persist a new product."""
    product = Product(**payload.model_dump())
    db.add(product)
    db.commit()
    db.refresh(product)
    return product


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
    filters = []
    order_by = [Product.created_at.desc()]

    if include_inactive:
        if category is not None:
            filters.append(Product.category == category.strip().lower())
    else:
        filters.extend(
            [
                Product.status == ProductStatus.ACTIVE.value,
                Product.stock > 0,
            ]
        )
        if category is not None:
            filters.append(Product.category == category.strip().lower())

    if seller_id is not None:
        filters.append(Product.seller_id == seller_id)

    if search_query is not None:
        normalized_query = search_query.strip()
        if normalized_query:
            search_term = f"%{normalized_query}%"
            title_match = Product.title.ilike(search_term)
            description_match = Product.description.ilike(search_term)
            filters.append(or_(title_match, description_match))
            relevance = case(
                (title_match, 0),
                (description_match, 1),
                else_=2,
            )
            order_by = [relevance.asc(), Product.created_at.desc()]

    base_query = select(Product).where(*filters)
    count_query = select(func.count()).select_from(Product).where(*filters)

    products = db.scalars(
        base_query.order_by(*order_by).limit(limit).offset(offset)
    ).all()
    total = db.scalar(count_query) or 0
    return products, total


def get_product(
    db: Session,
    product_id: UUID,
    *,
    include_inactive: bool = False,
) -> Product | None:
    """Fetch a single product, optionally including inactive ones."""
    query = select(Product).where(Product.id == product_id)
    if not include_inactive:
        query = query.where(Product.status == ProductStatus.ACTIVE.value)
    return db.scalar(query)


def update_product(db: Session, product_id: UUID, payload: ProductUpdate) -> Product | None:
    """Replace product data for an existing product."""
    product = get_product(db, product_id, include_inactive=True)
    if product is None:
        return None

    for field, value in payload.model_dump().items():
        setattr(product, field, value)

    db.add(product)
    db.commit()
    db.refresh(product)
    return product


def update_product_status(
    db: Session,
    product_id: UUID,
    payload: ProductStatusUpdate,
) -> Product | None:
    """Update the publication status for a product."""
    product = get_product(db, product_id, include_inactive=True)
    if product is None:
        return None

    product.status = payload.status.value
    db.add(product)
    db.commit()
    db.refresh(product)
    return product
