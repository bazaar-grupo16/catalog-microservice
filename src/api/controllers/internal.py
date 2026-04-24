"""
Internal controller — handles stock-status callbacks from the inventory service.
"""

from __future__ import annotations

from uuid import UUID

from sqlalchemy.orm import Session

from src.repositories import ProductRepository
from src.schemas import ProductResponse, StockStatusUpdateRequest
from src.services import ProductService
from src.services.inventory import InventoryService
from src.services.storage import StorageService


class InternalController:
    def __init__(self, db: Session) -> None:
        self.service = ProductService(
            product_repository=ProductRepository(db),
            storage_service=StorageService(),
            inventory_service=InventoryService(),
        )

    async def update_stock_status(
        self, product_id: UUID, payload: StockStatusUpdateRequest
    ) -> ProductResponse:
        product = self.service.update_stock_status(product_id, payload.has_stock)
        return ProductResponse(data=product)
