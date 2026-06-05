"""Database queries for product status history entries."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.models.product_status_history import ProductStatusHistory


class ProductStatusHistoryRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def stage(self, entry: ProductStatusHistory) -> None:
        """Add entry to the session without committing — committed with the next save."""
        self.db.add(entry)

    def find_by_product_id(self, product_id: UUID) -> list[ProductStatusHistory]:
        query = (
            select(ProductStatusHistory)
            .where(ProductStatusHistory.product_id == product_id)
            .order_by(ProductStatusHistory.changed_at.desc())
        )
        return list(self.db.scalars(query).all())
