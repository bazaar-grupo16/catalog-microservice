"""
Inventory service client.

Handles stock management through the inventory microservice via HTTP.
The base URL is read from the INVENTORY_SERVICE_URL environment variable.
"""

from __future__ import annotations

import os
from uuid import UUID

import httpx


class InventoryService:
    """HTTP client for the inventory microservice."""

    def __init__(self) -> None:
        self.base_url = os.environ["INVENTORY_SERVICE_URL"]

    def create_product_stock(self, product_id: UUID, initial_stock: int) -> None:
        """Register a new product in inventory with its initial stock."""
        httpx.post(
            f"{self.base_url}/internal/products/{product_id}/stock",
            json={"quantity": initial_stock},
        ).raise_for_status()

    def delete_product_stock(self, product_id: UUID) -> None:
        """Remove a product's stock entry from inventory."""
        httpx.delete(
            f"{self.base_url}/internal/products/{product_id}/stock",
        ).raise_for_status()

    def get_product_stock(self, product_id: UUID) -> int:
        """Return the current stock for a single product."""
        response = httpx.get(
            f"{self.base_url}/internal/products/{product_id}/stock",
        )
        response.raise_for_status()
        return response.json()["quantity"]

    def get_stocks(self, product_ids: list[UUID]) -> dict[UUID, int]:
        """Return stock levels for multiple products in a single call."""
        response = httpx.post(
            f"{self.base_url}/internal/products/stocks",
            json={"product_ids": [str(p) for p in product_ids]},
        )
        response.raise_for_status()
        return {UUID(k): v for k, v in response.json()["data"].items()}

    def update_product_stock(self, product_id: UUID, new_stock: int) -> None:
        """Update the stock level for a product in inventory."""
        httpx.put(
            f"{self.base_url}/internal/products/{product_id}/stock",
            json={"quantity": new_stock},
        ).raise_for_status()
