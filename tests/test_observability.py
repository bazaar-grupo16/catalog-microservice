"""Integration tests for observability behavior (correlation/request IDs)."""

from __future__ import annotations

from unittest.mock import patch
from uuid import UUID, uuid4

from fastapi.testclient import TestClient

from src.services.inventory import InventoryService
from tests.conftest import PRODUCT_IMAGE, make_auth_headers

AUTH_HEADERS = make_auth_headers("00000000-0000-0000-0000-000000000001")


def product_form(**overrides: object) -> dict[str, object]:
    data: dict[str, object] = {
        "title": "Mechanical Keyboard",
        "description": "Compact keyboard with tactile switches",
        "price": "129.90",
        "stock": "8",
        "category": "Peripherals",
    }
    data.update({key: str(value) for key, value in overrides.items()})
    return data


class _FakeResponse:
    def __init__(self, body: dict | None = None) -> None:
        self._body = body or {"data": {"quantity": 8}}

    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict:
        return self._body


class TestObservability:
    def test_echoes_x_request_id_in_response_headers(self, client: TestClient) -> None:
        request_id = str(uuid4())

        response = client.get("/products", headers={"X-Request-ID": request_id})

        assert response.status_code == 200
        assert response.headers["X-Request-ID"] == request_id
        assert response.headers["X-Correlation-ID"] == request_id

    def test_falls_back_to_x_correlation_id_when_request_id_is_missing(
        self, client: TestClient
    ) -> None:
        correlation_id = str(uuid4())

        response = client.get("/products", headers={"X-Correlation-ID": correlation_id})

        assert response.status_code == 200
        assert response.headers["X-Request-ID"] == correlation_id
        assert response.headers["X-Correlation-ID"] == correlation_id

    def test_generates_ids_when_no_header_is_provided(self, client: TestClient) -> None:
        response = client.get("/products")

        assert response.status_code == 200
        generated_request_id = response.headers["X-Request-ID"]
        generated_correlation_id = response.headers["X-Correlation-ID"]
        assert generated_request_id == generated_correlation_id
        UUID(generated_request_id)

    def test_forwards_ids_to_inventory_service(self, client: TestClient, monkeypatch) -> None:
        request_id = str(uuid4())
        outbound_headers: list[dict[str, str] | None] = []

        monkeypatch.setenv("INVENTORY_SERVICE_URL", "http://inventory-service")

        def fake_post(url, json=None, headers=None):
            outbound_headers.append(headers)
            return _FakeResponse()

        def fake_get(url, headers=None):
            outbound_headers.append(headers)
            return _FakeResponse({"data": {"quantity": 8}})

        with (
            patch("src.services.inventory.httpx.post", side_effect=fake_post),
            patch("src.services.inventory.httpx.get", side_effect=fake_get),
            patch("src.api.controllers.product.InventoryService", InventoryService),
            patch("src.api.controllers.internal.InventoryService", InventoryService),
        ):
            response = client.post(
                "/products",
                data=product_form(),
                files=PRODUCT_IMAGE,
                headers={**AUTH_HEADERS, "X-Request-ID": request_id},
            )

        assert response.status_code == 201
        assert len(outbound_headers) >= 2
        for headers in outbound_headers:
            assert headers is not None
            assert headers["X-Request-ID"] == request_id
            assert headers["X-Correlation-ID"] == request_id