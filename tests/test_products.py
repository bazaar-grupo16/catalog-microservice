"""
Integration tests for product CRUD endpoints.
"""

from __future__ import annotations

from uuid import uuid4

from fastapi.testclient import TestClient


def product_payload(**overrides: object) -> dict[str, object]:
    """Build a valid product payload for test cases."""
    payload: dict[str, object] = {
        "title": "Mechanical Keyboard",
        "description": "Compact keyboard with tactile switches",
        "price": "129.90",
        "stock": 8,
        "category": "Peripherals",
        "seller_id": str(uuid4()),
    }
    payload.update(overrides)
    return payload


class TestCreateProduct:
    """Creation scenarios for products."""

    def test_creates_product(self, client: TestClient) -> None:
        response = client.post("/products", json=product_payload())

        assert response.status_code == 201
        data = response.json()["data"]
        assert data["title"] == "Mechanical Keyboard"
        assert data["category"] == "peripherals"
        assert data["status"] == "active"
        assert "id" in data

    def test_rejects_invalid_payload(self, client: TestClient) -> None:
        response = client.post("/products", json=product_payload(price="-1", stock=-2))
        assert response.status_code == 422


class TestListProducts:
    """Listing scenarios with visibility rules and filters."""

    def test_hides_out_of_stock_products_by_default(self, client: TestClient) -> None:
        client.post("/products", json=product_payload(title="Visible Product"))
        client.post("/products", json=product_payload(title="Out of Stock", stock=0))

        response = client.get("/products")

        assert response.status_code == 200
        body = response.json()
        titles = [item["title"] for item in body["data"]]
        assert "Visible Product" in titles
        assert "Out of Stock" not in titles

    def test_filters_by_category(self, client: TestClient) -> None:
        client.post(
            "/products", json=product_payload(title="Keyboard", category="peripherals")
        )
        client.post(
            "/products", json=product_payload(title="Chair", category="furniture")
        )

        response = client.get("/products", params={"category": "peripherals"})

        assert response.status_code == 200
        body = response.json()
        assert body["total"] == 1
        assert body["data"][0]["category"] == "peripherals"

    def test_supports_pagination(self, client: TestClient) -> None:
        client.post("/products", json=product_payload(title="Product A"))
        client.post("/products", json=product_payload(title="Product B"))
        client.post("/products", json=product_payload(title="Product C"))

        response = client.get("/products", params={"limit": 2, "offset": 1})

        assert response.status_code == 200
        body = response.json()
        assert body["limit"] == 2
        assert body["offset"] == 1
        assert len(body["data"]) == 2

    def test_searches_by_title_before_description(self, client: TestClient) -> None:
        client.post(
            "/products",
            json=product_payload(
                title="Gaming Mouse",
                description="High precision pointer",
            ),
        )
        client.post(
            "/products",
            json=product_payload(
                title="Keyboard",
                description="Includes a gaming mouse pad",
            ),
        )

        response = client.get("/products", params={"search_query": "gaming mouse"})

        assert response.status_code == 200
        body = response.json()
        assert body["total"] == 2
        assert body["data"][0]["title"] == "Gaming Mouse"
        assert body["data"][1]["title"] == "Keyboard"

    def test_searches_by_description(self, client: TestClient) -> None:
        client.post(
            "/products",
            json=product_payload(
                title="Desk Lamp",
                description="Warm light for reading sessions",
            ),
        )

        response = client.get("/products", params={"search_query": "reading"})

        assert response.status_code == 200
        body = response.json()
        assert body["total"] == 1
        assert body["data"][0]["title"] == "Desk Lamp"

    def test_search_without_results_returns_empty_list(
        self, client: TestClient
    ) -> None:
        client.post("/products", json=product_payload())

        response = client.get("/products", params={"search_query": "nonexistent"})

        assert response.status_code == 200
        body = response.json()
        assert body["total"] == 0
        assert body["data"] == []

    def test_search_hides_out_of_stock_products(self, client: TestClient) -> None:
        client.post(
            "/products",
            json=product_payload(
                title="Available Camera",
                description="A camera for travel",
            ),
        )
        client.post(
            "/products",
            json=product_payload(
                title="Out of Stock Camera",
                description="A camera for travel",
                stock=0,
            ),
        )

        response = client.get("/products", params={"search_query": "camera"})

        assert response.status_code == 200
        body = response.json()
        assert body["total"] == 1
        assert body["data"][0]["title"] == "Available Camera"


class TestProductDetail:
    """Single-product retrieval scenarios."""

    def test_returns_product_detail(self, client: TestClient) -> None:
        create_response = client.post(
            "/products",
            json=product_payload(title="Rare Item", stock=0),
        )
        product_id = create_response.json()["data"]["id"]

        response = client.get(f"/products/{product_id}")

        assert response.status_code == 200
        data = response.json()["data"]
        assert data["title"] == "Rare Item"
        assert data["stock"] == 0

    def test_returns_404_for_nonexistent_product(self, client: TestClient) -> None:
        product_id = uuid4()

        response = client.get(f"/products/{product_id}")

        assert response.status_code == 404
        body = response.json()
        assert body["type"] == "about:blank"
        assert body["title"] == "Not Found"
        assert body["status"] == 404
        assert body["detail"] == "Product not found"
        assert body["instance"] == f"/products/{product_id}"


"""
class TestUpdateProduct:
    Update scenarios for full resource replacement and status changes.

    def test_updates_product_fields(self, client: TestClient) -> None:
        create_response = client.post("/products", json=product_payload())
        product_id = create_response.json()["id"]

        response = client.put(
            f"/products/{product_id}",
            json=product_payload(
                title="Updated Keyboard",
                price="149.99",
                stock=5,
                category="office",
            ),
        )

        assert response.status_code == 200
        body = response.json()
        assert body["title"] == "Updated Keyboard"
        assert body["price"] == "149.99"
        assert body["stock"] == 5
        assert body["category"] == "office"

    def test_disables_product(self, client: TestClient) -> None:
        create_response = client.post("/products", json=product_payload())
        product_id = create_response.json()["id"]

        response = client.patch(
            f"/products/{product_id}/status",
            json={"status": "inactive"},
        )

        assert response.status_code == 200
        assert response.json()["status"] == "inactive"

        list_response = client.get("/products")
        assert product_id not in {item["id"] for item in list_response.json()["items"]}
"""
