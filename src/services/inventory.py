"""
Inventory service client.

Handles stock management through the inventory microservice.
Currently returns hardcoded values while the inventory service is being implemented.
"""

from __future__ import annotations

import logging
from uuid import UUID

logger = logging.getLogger(__name__)

# Hardcoded stock value used until the inventory service is implemented.
_STUB_STOCK = 10


class InventoryService:
    """HTTP client for the inventory microservice.

    All methods currently return stub values.  Replace each method body with
    real HTTP calls once the inventory service is available.
    """

    def create_product_stock(self, product_id: UUID, initial_stock: int) -> None:
        """Register a new product in inventory with its initial stock."""
        logger.info(
            "[inventory stub] create_product_stock product_id=%s initial_stock=%d",
            product_id,
            initial_stock,
        )

    def delete_product_stock(self, product_id: UUID) -> None:
        """Remove a product's stock entry from inventory."""
        logger.info(
            "[inventory stub] delete_product_stock product_id=%s",
            product_id,
        )

    def get_product_stock(self, product_id: UUID) -> int:
        """Return the current stock for a single product."""
        logger.debug(
            "[inventory stub] get_product_stock product_id=%s -> %d",
            product_id,
            _STUB_STOCK,
        )
        return _STUB_STOCK

    def get_stocks(self, product_ids: list[UUID]) -> dict[UUID, int]:
        """Return stock levels for multiple products in a single call."""
        logger.debug(
            "[inventory stub] get_stocks count=%d -> %d each",
            len(product_ids),
            _STUB_STOCK,
        )
        return {pid: _STUB_STOCK for pid in product_ids}

    def update_product_stock(self, product_id: UUID, new_stock: int) -> None:
        """Update the stock level for a product in inventory."""
        logger.info(
            "[inventory stub] update_product_stock product_id=%s new_stock=%d",
            product_id,
            new_stock,
        )
