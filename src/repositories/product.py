"""
Database queries for product entities.
"""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import case, func, or_, select
from sqlalchemy.orm import Session

from src.core.enums import ProductSortBy, ProductStatus, SortOrder
from src.dtos import ProductFilterDTO
from src.models import Product


_FUZZY_THRESHOLD = 0.3


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

    def find_by_id(self, product_id: UUID) -> Product | None:
        """Fetch a single product by primary key, including inactive ones."""
        query = select(Product).where(Product.id == product_id)
        return self.db.scalar(query)

    def delete(self, product: Product) -> None:
        """Delete a product record from the database."""
        self.db.delete(product)
        self.db.commit()

    def find_all(self, dto: ProductFilterDTO) -> tuple[list[Product], int]:
        """Return a paginated product list with optional filters applied."""
        filters = []
        order_by = [Product.created_at.desc()]

        if not dto.include_blocked:
            filters.append(~Product.is_blocked)

        if dto.include_inactive:
            if dto.category is not None:
                filters.append(Product.category == dto.category.strip().lower())
        else:
            filters.append(
                Product.status.notin_(
                    [
                        ProductStatus.INACTIVE.value,
                        ProductStatus.OUT_OF_STOCK.value,
                    ]
                )
            )
            if dto.category is not None:
                filters.append(Product.category == dto.category.strip().lower())

        if dto.seller_id is not None:
            filters.append(Product.seller_id == dto.seller_id)

        if dto.min_price is not None:
            filters.append(Product.price >= dto.min_price)

        if dto.max_price is not None:
            filters.append(Product.price <= dto.max_price)

        if dto.search_query is not None:
            normalized_query = dto.search_query.strip()
            if normalized_query:
                search_term = f"%{normalized_query}%"
                title_ilike = Product.title.ilike(search_term)
                description_ilike = Product.description.ilike(search_term)
                title_fuzzy = func.similarity(Product.title, normalized_query) > _FUZZY_THRESHOLD
                description_fuzzy = func.similarity(Product.description, normalized_query) > _FUZZY_THRESHOLD
                filters.append(or_(title_ilike, description_ilike, title_fuzzy, description_fuzzy))
                if dto.sort_by is None:
                    relevance = case(
                        (title_ilike, 0),
                        (description_ilike, 1),
                        (title_fuzzy, 2),
                        (description_fuzzy, 3),
                        else_=4,
                    )
                    order_by = [relevance.asc(), Product.created_at.desc()]

        if dto.sort_by is not None:
            sort_col = {
                ProductSortBy.PRICE: Product.price,
                ProductSortBy.CREATED_AT: Product.created_at,
                ProductSortBy.TITLE: Product.title,
            }[dto.sort_by]
            direction = (
                sort_col.asc() if dto.order == SortOrder.ASC else sort_col.desc()
            )
            order_by = [direction]

        base_query = select(Product).where(*filters)
        count_query = select(func.count()).select_from(Product).where(*filters)

        products = self.db.scalars(
            base_query.order_by(*order_by).limit(dto.limit).offset(dto.offset)
        ).all()
        total = self.db.scalar(count_query) or 0
        return list(products), total
