"""
Integration tests for product status history — GET /products/{id}/status-history.

Covers every code path that stages a history entry:
  - Seller manually changes status
  - Seller patches stock (triggering automatic status transition)
  - System stock-status callback (inventory service)
  - Admin block / unblock
  - No-op operations that must NOT produce entries
"""

from __future__ import annotations

from uuid import uuid4

from fastapi.testclient import TestClient

from tests.conftest import PRODUCT_IMAGE, make_auth_headers

SELLER_ID = "00000000-0000-0000-0000-000000000001"
ADMIN_ID = "00000000-0000-0000-0000-000000000002"

AUTH_HEADERS = make_auth_headers(SELLER_ID)
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


class TestStatusHistory:
    """GET /products/{id}/status-history"""

    def _create(self, client: TestClient, **kwargs: object) -> str:
        r = client.post(
            "/products", data=product_form(**kwargs), files=PRODUCT_IMAGE, headers=AUTH_HEADERS
        )
        assert r.status_code == 201
        return r.json()["data"]["id"]

    def _history(self, client: TestClient, pid: str):
        return client.get(f"/products/{pid}/status-history", headers=AUTH_HEADERS)

    # ── Baseline ────────────────────────────────────────────────────────────

    def test_new_product_has_no_history(self, client: TestClient) -> None:
        pid = self._create(client)

        r = self._history(client, pid)

        assert r.status_code == 200
        assert r.json()["data"] == []

    def test_returns_404_for_nonexistent_product(self, client: TestClient) -> None:
        r = client.get(f"/products/{uuid4()}/status-history", headers=AUTH_HEADERS)

        assert r.status_code == 404
        assert r.json()["detail"] == "Product not found"

    # ── Seller status changes ────────────────────────────────────────────────

    def test_seller_deactivation_creates_entry(self, client: TestClient) -> None:
        pid = self._create(client)

        client.patch(f"/products/{pid}", json={"status": "inactive"}, headers=AUTH_HEADERS)

        entries = self._history(client, pid).json()["data"]
        assert len(entries) == 1
        assert entries[0]["previousState"] == "active"
        assert entries[0]["newState"] == "inactive"
        assert entries[0]["changedByRole"] == "seller"
        assert entries[0]["changedBy"] == SELLER_ID

    def test_seller_reactivation_creates_entry(self, client: TestClient) -> None:
        pid = self._create(client)
        client.patch(f"/products/{pid}", json={"status": "inactive"}, headers=AUTH_HEADERS)

        client.patch(f"/products/{pid}", json={"status": "active"}, headers=AUTH_HEADERS)

        entries = self._history(client, pid).json()["data"]
        assert len(entries) == 2
        assert entries[0]["previousState"] == "inactive"
        assert entries[0]["newState"] == "active"

    def test_no_entry_when_state_unchanged(self, client: TestClient) -> None:
        pid = self._create(client)

        client.patch(f"/products/{pid}", json={"title": "New Title"}, headers=AUTH_HEADERS)

        assert self._history(client, pid).json()["data"] == []

    # ── Stock changes via seller PATCH ───────────────────────────────────────

    def test_stock_zeroed_by_seller_creates_entry(self, client: TestClient) -> None:
        pid = self._create(client)  # stock=10 → active

        client.patch(f"/products/{pid}", json={"stock": 0}, headers=AUTH_HEADERS)

        entries = self._history(client, pid).json()["data"]
        assert len(entries) == 1
        assert entries[0]["previousState"] == "active"
        assert entries[0]["newState"] == "out_of_stock"
        assert entries[0]["changedByRole"] == "seller"

    def test_stock_restored_by_seller_creates_entry(self, client: TestClient) -> None:
        pid = self._create(client, stock=0)  # out_of_stock

        client.patch(f"/products/{pid}", json={"stock": 5}, headers=AUTH_HEADERS)

        entries = self._history(client, pid).json()["data"]
        assert len(entries) == 1
        assert entries[0]["previousState"] == "out_of_stock"
        assert entries[0]["newState"] == "active"
        assert entries[0]["changedByRole"] == "seller"

    # ── System stock-status callback ─────────────────────────────────────────

    def test_system_depletes_stock_creates_entry(self, client: TestClient) -> None:
        pid = self._create(client)  # active

        client.patch(f"/internal/products/{pid}/stock-status", json={"has_stock": False})

        entries = self._history(client, pid).json()["data"]
        assert len(entries) == 1
        assert entries[0]["previousState"] == "active"
        assert entries[0]["newState"] == "out_of_stock"
        assert entries[0]["changedByRole"] == "system"
        assert entries[0]["changedBy"] is None

    def test_system_restores_stock_creates_entry(self, client: TestClient) -> None:
        pid = self._create(client)
        client.patch(f"/internal/products/{pid}/stock-status", json={"has_stock": False})

        client.patch(f"/internal/products/{pid}/stock-status", json={"has_stock": True})

        entries = self._history(client, pid).json()["data"]
        assert len(entries) == 2
        assert entries[0]["previousState"] == "out_of_stock"
        assert entries[0]["newState"] == "active"
        assert entries[0]["changedByRole"] == "system"
        assert entries[0]["changedBy"] is None

    def test_system_noop_on_inactive_creates_no_entry(self, client: TestClient) -> None:
        pid = self._create(client)
        client.patch(f"/products/{pid}", json={"status": "inactive"}, headers=AUTH_HEADERS)

        client.patch(f"/internal/products/{pid}/stock-status", json={"has_stock": False})

        entries = self._history(client, pid).json()["data"]
        assert len(entries) == 1  # only the seller deactivation
        assert entries[0]["changedByRole"] == "seller"

    # ── Admin block / unblock ────────────────────────────────────────────────

    def test_admin_block_creates_entry(self, client: TestClient) -> None:
        pid = self._create(client)

        client.patch(f"/products/{pid}/block", headers=ADMIN_HEADERS)

        entries = self._history(client, pid).json()["data"]
        assert len(entries) == 1
        assert entries[0]["previousState"] == "active"
        assert entries[0]["newState"] == "blocked"
        assert entries[0]["changedByRole"] == "admin"
        assert entries[0]["changedBy"] == ADMIN_ID

    def test_admin_unblock_creates_entry(self, client: TestClient) -> None:
        pid = self._create(client)
        client.patch(f"/products/{pid}/block", headers=ADMIN_HEADERS)

        client.patch(f"/products/{pid}/unblock", headers=ADMIN_HEADERS)

        entries = self._history(client, pid).json()["data"]
        assert len(entries) == 2
        assert entries[0]["previousState"] == "blocked"
        assert entries[0]["newState"] == "active"
        assert entries[0]["changedByRole"] == "admin"

    def test_blocking_already_blocked_product_creates_no_entry(
        self, client: TestClient
    ) -> None:
        pid = self._create(client)
        client.patch(f"/products/{pid}/block", headers=ADMIN_HEADERS)

        client.patch(f"/products/{pid}/block", headers=ADMIN_HEADERS)  # noop

        entries = self._history(client, pid).json()["data"]
        assert len(entries) == 1

    def test_unblock_restores_previous_state(self, client: TestClient) -> None:
        pid = self._create(client)
        client.patch(f"/products/{pid}", json={"status": "inactive"}, headers=AUTH_HEADERS)
        client.patch(f"/products/{pid}/block", headers=ADMIN_HEADERS)

        client.patch(f"/products/{pid}/unblock", headers=ADMIN_HEADERS)

        entries = self._history(client, pid).json()["data"]
        assert entries[0]["previousState"] == "blocked"
        assert entries[0]["newState"] == "inactive"

    # ── Ordering ─────────────────────────────────────────────────────────────

    def test_entries_ordered_newest_first(self, client: TestClient) -> None:
        pid = self._create(client)
        client.patch(f"/products/{pid}", json={"status": "inactive"}, headers=AUTH_HEADERS)
        client.patch(f"/products/{pid}", json={"status": "active"}, headers=AUTH_HEADERS)
        client.patch(f"/products/{pid}", json={"stock": 0}, headers=AUTH_HEADERS)

        entries = self._history(client, pid).json()["data"]

        assert len(entries) == 3
        assert [e["newState"] for e in entries] == ["out_of_stock", "active", "inactive"]
