"""
Internal controller — handles stock-status callbacks from the inventory service.
"""

from __future__ import annotations

from uuid import UUID

from sqlalchemy.orm import Session

from src.repositories import ProductRepository, ProductStatusHistoryRepository
from src.schemas import ProductResponse, SellerBlockRequest, SellerBlockResponse, StockStatusUpdateRequest
from src.services import ProductService
from src.services.inventory import InventoryService
from src.services.storage import StorageService


class InternalController:
    def __init__(self, db: Session) -> None:
        self.service = ProductService(
            product_repository=ProductRepository(db),
            storage_service=StorageService(),
            inventory_service=InventoryService(),
            history_repository=ProductStatusHistoryRepository(db),
        )

    async def update_stock_status(
        self, product_id: UUID, payload: StockStatusUpdateRequest
    ) -> ProductResponse:
        product = self.service.update_stock_status(product_id, payload.has_stock)
        return ProductResponse(data=product)

    async def block_seller_products(
        self, seller_id: UUID, payload: SellerBlockRequest
    ) -> SellerBlockResponse:
        affected = self.service.block_seller_products(seller_id, payload.admin_id)
        return SellerBlockResponse(affected=affected)

    async def unblock_seller_products(
        self, seller_id: UUID, payload: SellerBlockRequest
    ) -> SellerBlockResponse:
        affected = self.service.unblock_seller_products(seller_id, payload.admin_id)
        return SellerBlockResponse(affected=affected)
