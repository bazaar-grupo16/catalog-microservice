"""
Integration tests for seller-level block/unblock endpoints.

  PATCH /internal/sellers/{seller_id}/block
  PATCH /internal/sellers/{seller_id}/unblock

Covers: bulk blocking, idempotency, catalog visibility, and cross-seller isolation.
"""

from __future__ import annotations

from uuid import uuid4

from fastapi.testclient import TestClient

from tests.conftest import PRODUCT_IMAGE, make_auth_headers

SELLER_ID = "00000000-0000-0000-0000-000000000010"
OTHER_SELLER_ID = "00000000-0000-0000-0000-000000000011"
ADMIN_ID = "00000000-0000-0000-0000-000000000002"

SELLER_HEADERS = make_auth_headers(SELLER_ID)
OTHER_SELLER_HEADERS = make_auth_headers(OTHER_SELLER_ID)
ADMIN_HEADERS = make_auth_headers(ADMIN_ID)


def _create_product(client: TestClient, seller_headers: dict, **kwargs: object) -> str:
    data = {
        "title": "Test Product",
        "description": "A product for testing",
        "price": "50.00",
        "stock": "10",
        "category": "electronics",
    }
    data.update({k: str(v) for k, v in kwargs.items()})
    r = client.post("/products", data=data, files=PRODUCT_IMAGE, headers=seller_headers)
    assert r.status_code == 201
    return r.json()["data"]["id"]


class TestBlockSellerProducts:
    """PATCH /internal/sellers/{seller_id}/block"""

    def test_returns_200(self, client: TestClient) -> None:
        _create_product(client, SELLER_HEADERS)

        r = client.patch(f"/internal/sellers/{SELLER_ID}/block", json={})

        assert r.status_code == 200

    def test_returns_affected_count(self, client: TestClient) -> None:
        _create_product(client, SELLER_HEADERS)
        _create_product(client, SELLER_HEADERS)

        r = client.patch(f"/internal/sellers/{SELLER_ID}/block", json={})

        assert r.json()["affected"] == 2

    def test_blocked_products_hidden_from_catalog(self, client: TestClient) -> None:
        pid1 = _create_product(client, SELLER_HEADERS)
        pid2 = _create_product(client, SELLER_HEADERS)

        client.patch(f"/internal/sellers/{SELLER_ID}/block", json={})

        r = client.get("/products")
        ids = [p["id"] for p in r.json()["data"]]
        assert pid1 not in ids
        assert pid2 not in ids

    def test_blocked_products_visible_with_include_blocked(self, client: TestClient) -> None:
        pid = _create_product(client, SELLER_HEADERS)

        client.patch(f"/internal/sellers/{SELLER_ID}/block", json={})

        r = client.get("/products", params={"include_blocked": "true"})
        ids = [p["id"] for p in r.json()["data"]]
        assert pid in ids

    def test_does_not_affect_other_sellers(self, client: TestClient) -> None:
        _create_product(client, SELLER_HEADERS)
        other_pid = _create_product(client, OTHER_SELLER_HEADERS)

        client.patch(f"/internal/sellers/{SELLER_ID}/block", json={})

        r = client.get("/products")
        ids = [p["id"] for p in r.json()["data"]]
        assert other_pid in ids

    def test_idempotent_when_already_blocked(self, client: TestClient) -> None:
        _create_product(client, SELLER_HEADERS)
        client.patch(f"/internal/sellers/{SELLER_ID}/block", json={})

        r = client.patch(f"/internal/sellers/{SELLER_ID}/block", json={})

        assert r.status_code == 200
        assert r.json()["affected"] == 0

    def test_zero_affected_for_seller_with_no_products(self, client: TestClient) -> None:
        r = client.patch(f"/internal/sellers/{uuid4()}/block", json={})

        assert r.status_code == 200
        assert r.json()["affected"] == 0

    def test_accepts_admin_id_in_body(self, client: TestClient) -> None:
        _create_product(client, SELLER_HEADERS)

        r = client.patch(
            f"/internal/sellers/{SELLER_ID}/block",
            json={"admin_id": ADMIN_ID},
        )

        assert r.status_code == 200
        assert r.json()["affected"] == 1


class TestUnblockSellerProducts:
    """PATCH /internal/sellers/{seller_id}/unblock"""

    def _block_seller(self, client: TestClient) -> None:
        r = client.patch(f"/internal/sellers/{SELLER_ID}/block", json={})
        assert r.status_code == 200

    def test_returns_200(self, client: TestClient) -> None:
        _create_product(client, SELLER_HEADERS)
        self._block_seller(client)

        r = client.patch(f"/internal/sellers/{SELLER_ID}/unblock", json={})

        assert r.status_code == 200

    def test_returns_affected_count(self, client: TestClient) -> None:
        _create_product(client, SELLER_HEADERS)
        _create_product(client, SELLER_HEADERS)
        self._block_seller(client)

        r = client.patch(f"/internal/sellers/{SELLER_ID}/unblock", json={})

        assert r.json()["affected"] == 2

    def test_unblocked_products_visible_in_catalog(self, client: TestClient) -> None:
        pid1 = _create_product(client, SELLER_HEADERS)
        pid2 = _create_product(client, SELLER_HEADERS)
        self._block_seller(client)

        client.patch(f"/internal/sellers/{SELLER_ID}/unblock", json={})

        r = client.get("/products")
        ids = [p["id"] for p in r.json()["data"]]
        assert pid1 in ids
        assert pid2 in ids

    def test_does_not_affect_other_sellers(self, client: TestClient) -> None:
        _create_product(client, SELLER_HEADERS)
        other_pid = _create_product(client, OTHER_SELLER_HEADERS)
        client.patch(f"/internal/sellers/{SELLER_ID}/block", json={})
        client.patch(f"/internal/sellers/{OTHER_SELLER_ID}/block", json={})

        client.patch(f"/internal/sellers/{SELLER_ID}/unblock", json={})

        r = client.get("/products")
        ids = [p["id"] for p in r.json()["data"]]
        assert other_pid not in ids

    def test_idempotent_when_already_unblocked(self, client: TestClient) -> None:
        _create_product(client, SELLER_HEADERS)

        r = client.patch(f"/internal/sellers/{SELLER_ID}/unblock", json={})

        assert r.status_code == 200
        assert r.json()["affected"] == 0

    def test_zero_affected_for_seller_with_no_products(self, client: TestClient) -> None:
        r = client.patch(f"/internal/sellers/{uuid4()}/unblock", json={})

        assert r.status_code == 200
        assert r.json()["affected"] == 0

    def test_individually_blocked_product_stays_blocked_after_seller_unblock(
        self, client: TestClient
    ) -> None:
        pid_individual = _create_product(client, SELLER_HEADERS)
        pid_seller = _create_product(client, SELLER_HEADERS)

        # Block one product individually
        client.patch(f"/products/{pid_individual}/block", headers=ADMIN_HEADERS)

        # Block the whole seller (pid_individual is already blocked, only pid_seller gets flagged)
        client.patch(f"/internal/sellers/{SELLER_ID}/block", json={})

        # Unblock the seller
        r = client.patch(f"/internal/sellers/{SELLER_ID}/unblock", json={})
        assert r.json()["affected"] == 1  # only pid_seller

        catalog = [p["id"] for p in client.get("/products").json()["data"]]
        assert pid_seller in catalog
        assert pid_individual not in catalog  # still blocked

    def test_individually_blocked_before_seller_block_stays_blocked(
        self, client: TestClient
    ) -> None:
        pid = _create_product(client, SELLER_HEADERS)

        # Individually block, then block seller (no-op for this product, no seller_block history)
        client.patch(f"/products/{pid}/block", headers=ADMIN_HEADERS)
        client.patch(f"/internal/sellers/{SELLER_ID}/block", json={})

        r = client.patch(f"/internal/sellers/{SELLER_ID}/unblock", json={})

        assert r.json()["affected"] == 0
        data = client.get(f"/products/{pid}").json()["data"]
        assert data["adminDisabled"] is True
