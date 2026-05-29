"""
Tests for the inventory HTTP client contract.
"""

from __future__ import annotations

from uuid import uuid4

import httpx

from src.services.inventory import InventoryService


def test_get_product_stock_reads_wrapped_inventory_response(monkeypatch) -> None:
    product_id = uuid4()
    monkeypatch.setenv("INVENTORY_SERVICE_URL", "http://inventory-service")

    def fake_get(url: str, headers: dict[str, str] | None = None) -> httpx.Response:
        assert url == f"http://inventory-service/internal/products/{product_id}/stock"
        return httpx.Response(
            200,
            request=httpx.Request("GET", url),
            json={
                "data": {
                    "product_id": str(product_id),
                    "quantity": 7,
                    "updated_at": "2026-04-15T00:00:00Z",
                }
            },
        )

    monkeypatch.setattr(httpx, "get", fake_get)

    assert InventoryService().get_product_stock(product_id) == 7


def test_get_product_stock_accepts_legacy_unwrapped_response(monkeypatch) -> None:
    product_id = uuid4()
    monkeypatch.setenv("INVENTORY_SERVICE_URL", "http://inventory-service")

    def fake_get(url: str, headers: dict[str, str] | None = None) -> httpx.Response:
        assert url == f"http://inventory-service/internal/products/{product_id}/stock"
        return httpx.Response(
            200,
            request=httpx.Request("GET", url),
            json={"quantity": 3},
        )

    monkeypatch.setattr(httpx, "get", fake_get)

    assert InventoryService().get_product_stock(product_id) == 3
