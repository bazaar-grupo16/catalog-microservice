"""
Integration tests for block/unblock product endpoints.

  PATCH /products/{id}/block
  PATCH /products/{id}/unblock

Covers: HTTP status codes, response body shape, catalog visibility effects,
idempotency, and auth/not-found error cases.
"""

from __future__ import annotations

from uuid import uuid4

from fastapi.testclient import TestClient

from tests.conftest import PRODUCT_IMAGE, make_auth_headers

SELLER_ID = "00000000-0000-0000-0000-000000000001"
ADMIN_ID = "00000000-0000-0000-0000-000000000002"

SELLER_HEADERS = make_auth_headers(SELLER_ID)
ADMIN_HEADERS = make_auth_headers(ADMIN_ID)


def product_form(**overrides: object) -> dict[str, object]:
    data: dict[str, object] = {
        "title": "Test Product",
        "description": "A product for testing",
        "price": "50.00",
        "stock": "10",
        "category": "electronics",
    }
    data.update({k: str(v) for k, v in overrides.items()})
    return data


class TestBlockProduct:
    """PATCH /products/{id}/block"""

    def _create(self, client: TestClient, **kwargs: object) -> str:
        r = client.post(
            "/products", data=product_form(**kwargs), files=PRODUCT_IMAGE, headers=SELLER_HEADERS
        )
        assert r.status_code == 201
        return r.json()["data"]["id"]

    def test_block_returns_200(self, client: TestClient) -> None:
        pid = self._create(client)

        r = client.patch(f"/products/{pid}/block", headers=ADMIN_HEADERS)

        assert r.status_code == 200

    def test_block_sets_admin_disabled_true(self, client: TestClient) -> None:
        pid = self._create(client)

        r = client.patch(f"/products/{pid}/block", headers=ADMIN_HEADERS)

        assert r.json()["data"]["adminDisabled"] is True

    def test_block_response_contains_product_data(self, client: TestClient) -> None:
        pid = self._create(client)

        r = client.patch(f"/products/{pid}/block", headers=ADMIN_HEADERS)

        data = r.json()["data"]
        assert data["id"] == pid
        assert "title" in data
        assert "status" in data

    def test_block_returns_404_for_unknown_product(self, client: TestClient) -> None:
        r = client.patch(f"/products/{uuid4()}/block", headers=ADMIN_HEADERS)

        assert r.status_code == 404
        assert r.json()["detail"] == "Product not found"

    def test_block_returns_401_without_auth(self, client: TestClient) -> None:
        pid = self._create(client)

        r = client.patch(f"/products/{pid}/block")

        assert r.status_code == 401

    def test_block_already_blocked_is_idempotent(self, client: TestClient) -> None:
        pid = self._create(client)
        client.patch(f"/products/{pid}/block", headers=ADMIN_HEADERS)

        r = client.patch(f"/products/{pid}/block", headers=ADMIN_HEADERS)

        assert r.status_code == 200
        assert r.json()["data"]["adminDisabled"] is True

    def test_blocked_product_hidden_from_catalog(self, client: TestClient) -> None:
        pid = self._create(client)
        client.patch(f"/products/{pid}/block", headers=ADMIN_HEADERS)

        r = client.get("/products")

        ids = [p["id"] for p in r.json()["data"]]
        assert pid not in ids

    def test_blocked_product_visible_with_include_blocked(self, client: TestClient) -> None:
        pid = self._create(client)
        client.patch(f"/products/{pid}/block", headers=ADMIN_HEADERS)

        r = client.get("/products", params={"include_blocked": "true"})

        ids = [p["id"] for p in r.json()["data"]]
        assert pid in ids

    def test_blocked_product_still_accessible_by_id(self, client: TestClient) -> None:
        pid = self._create(client)
        client.patch(f"/products/{pid}/block", headers=ADMIN_HEADERS)

        r = client.get(f"/products/{pid}")

        assert r.status_code == 200
        assert r.json()["data"]["adminDisabled"] is True


class TestUnblockProduct:
    """PATCH /products/{id}/unblock"""

    def _create(self, client: TestClient, **kwargs: object) -> str:
        r = client.post(
            "/products", data=product_form(**kwargs), files=PRODUCT_IMAGE, headers=SELLER_HEADERS
        )
        assert r.status_code == 201
        return r.json()["data"]["id"]

    def _block(self, client: TestClient, pid: str) -> None:
        r = client.patch(f"/products/{pid}/block", headers=ADMIN_HEADERS)
        assert r.status_code == 200

    def test_unblock_returns_200(self, client: TestClient) -> None:
        pid = self._create(client)
        self._block(client, pid)

        r = client.patch(f"/products/{pid}/unblock", headers=ADMIN_HEADERS)

        assert r.status_code == 200

    def test_unblock_sets_admin_disabled_false(self, client: TestClient) -> None:
        pid = self._create(client)
        self._block(client, pid)

        r = client.patch(f"/products/{pid}/unblock", headers=ADMIN_HEADERS)

        assert r.json()["data"]["adminDisabled"] is False

    def test_unblock_response_contains_product_data(self, client: TestClient) -> None:
        pid = self._create(client)
        self._block(client, pid)

        r = client.patch(f"/products/{pid}/unblock", headers=ADMIN_HEADERS)

        data = r.json()["data"]
        assert data["id"] == pid
        assert "title" in data
        assert "status" in data

    def test_unblock_returns_404_for_unknown_product(self, client: TestClient) -> None:
        r = client.patch(f"/products/{uuid4()}/unblock", headers=ADMIN_HEADERS)

        assert r.status_code == 404
        assert r.json()["detail"] == "Product not found"

    def test_unblock_returns_401_without_auth(self, client: TestClient) -> None:
        pid = self._create(client)
        self._block(client, pid)

        r = client.patch(f"/products/{pid}/unblock")

        assert r.status_code == 401

    def test_unblock_not_blocked_is_idempotent(self, client: TestClient) -> None:
        pid = self._create(client)

        r = client.patch(f"/products/{pid}/unblock", headers=ADMIN_HEADERS)

        assert r.status_code == 200
        assert r.json()["data"]["adminDisabled"] is False

    def test_unblocked_product_visible_in_catalog(self, client: TestClient) -> None:
        pid = self._create(client)
        self._block(client, pid)

        client.patch(f"/products/{pid}/unblock", headers=ADMIN_HEADERS)

        r = client.get("/products")
        ids = [p["id"] for p in r.json()["data"]]
        assert pid in ids

    def test_unblock_preserves_seller_status(self, client: TestClient) -> None:
        pid = self._create(client)
        client.patch(f"/products/{pid}", json={"status": "inactive"}, headers=SELLER_HEADERS)
        self._block(client, pid)

        r = client.patch(f"/products/{pid}/unblock", headers=ADMIN_HEADERS)

        data = r.json()["data"]
        assert data["adminDisabled"] is False
        assert data["status"] == "inactive"
