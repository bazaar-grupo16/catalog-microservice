"""
Database queries for product entities.
"""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import case, func, or_, select
from sqlalchemy.orm import Session

from src.core.enums import ProductStatus
from src.models import Product


class ProductRepository:
    """Repository for product database operations."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def create(self, product: Product) -> Product:
        """Persist a new product and return the refreshed instance."""
        self.db.add(product)
        self.db.commit()
        self.db.refresh(product)
        return product

    def save(self, product: Product) -> Product:
        """Persist changes to an existing product and return the refreshed instance."""
        self.db.add(product)
        self.db.commit()
        self.db.refresh(product)
        return product

    def find_by_id(
        self,
        product_id: UUID,
        *,
        include_inactive: bool = False,
    ) -> Product | None:
        """Fetch a single product by primary key, optionally including inactive ones."""
        query = select(Product).where(Product.id == product_id)
        if not include_inactive:
            query = query.where(Product.status == ProductStatus.ACTIVE.value)
        return self.db.scalar(query)

    def find_all(
        self,
        *,
        limit: int,
        offset: int,
        search_query: str | None = None,
        category: str | None = None,
        seller_id: UUID | None = None,
        include_inactive: bool = False,
    ) -> tuple[list[Product], int]:
        """Return a paginated product list with optional filters applied."""
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

        products = self.db.scalars(
            base_query.order_by(*order_by).limit(limit).offset(offset)
        ).all()
        total = self.db.scalar(count_query) or 0
        return list(products), total
