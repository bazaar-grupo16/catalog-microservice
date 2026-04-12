"""
Integration tests for product CRUD endpoints.
"""

from __future__ import annotations

from uuid import uuid4

from fastapi.testclient import TestClient

from tests.conftest import PRODUCT_IMAGE


def product_form(**overrides: object) -> dict[str, object]:
    """Build multipart form data for product creation."""
    data: dict[str, object] = {
        "title": "Mechanical Keyboard",
        "description": "Compact keyboard with tactile switches",
        "price": "129.90",
        "stock": "8",
        "category": "Peripherals",
        "seller_id": str(uuid4()),
    }
    data.update({k: str(v) for k, v in overrides.items()})
    return data


class TestCreateProduct:
    """Creation scenarios for products."""

    def test_creates_product(self, client: TestClient) -> None:
        response = client.post("/products", data=product_form(), files=PRODUCT_IMAGE)

        assert response.status_code == 201
        data = response.json()["data"]
        assert data["title"] == "Mechanical Keyboard"
        assert data["category"] == "peripherals"
        assert data["status"] == "active"
        assert len(data["images"]) == 1
        assert "id" in data

    def test_rejects_invalid_payload(self, client: TestClient) -> None:
        response = client.post(
            "/products",
            data=product_form(price="-1", stock="-2"),
            files=PRODUCT_IMAGE,
        )
        assert response.status_code == 422

    def test_rejects_blank_title(self, client: TestClient) -> None:
        response = client.post(
            "/products", data=product_form(title="   "), files=PRODUCT_IMAGE
        )
        assert response.status_code == 422

    def test_rejects_invalid_image_mime_type(self, client: TestClient) -> None:
        response = client.post(
            "/products",
            data=product_form(),
            files=[("files", ("doc.pdf", b"content", "application/pdf"))],
        )
        assert response.status_code == 400

    def test_rejects_oversized_image(self, client: TestClient) -> None:
        big = b"x" * (10 * 1024 * 1024 + 1)
        response = client.post(
            "/products",
            data=product_form(),
            files=[("files", ("big.jpg", big, "image/jpeg"))],
        )
        assert response.status_code == 400


class TestListProducts:
    """Listing scenarios with visibility rules and filters."""

    def test_hides_out_of_stock_products_by_default(self, client: TestClient) -> None:
        client.post(
            "/products", data=product_form(title="Visible Product"), files=PRODUCT_IMAGE
        )
        client.post(
            "/products",
            data=product_form(title="Out of Stock", stock="0"),
            files=PRODUCT_IMAGE,
        )

        response = client.get("/products")

        assert response.status_code == 200
        titles = [item["title"] for item in response.json()["data"]]
        assert "Visible Product" in titles
        assert "Out of Stock" not in titles

    def test_filters_by_category(self, client: TestClient) -> None:
        client.post(
            "/products",
            data=product_form(title="Keyboard", category="peripherals"),
            files=PRODUCT_IMAGE,
        )
        client.post(
            "/products",
            data=product_form(title="Chair", category="furniture"),
            files=PRODUCT_IMAGE,
        )

        response = client.get("/products", params={"category": "peripherals"})

        assert response.status_code == 200
        body = response.json()
        assert body["total"] == 1
        assert body["data"][0]["category"] == "peripherals"

    def test_supports_pagination(self, client: TestClient) -> None:
        client.post(
            "/products", data=product_form(title="Product A"), files=PRODUCT_IMAGE
        )
        client.post(
            "/products", data=product_form(title="Product B"), files=PRODUCT_IMAGE
        )
        client.post(
            "/products", data=product_form(title="Product C"), files=PRODUCT_IMAGE
        )

        response = client.get("/products", params={"limit": 2, "offset": 1})

        assert response.status_code == 200
        body = response.json()
        assert body["limit"] == 2
        assert body["offset"] == 1
        assert len(body["data"]) == 2

    def test_searches_by_title_before_description(self, client: TestClient) -> None:
        client.post(
            "/products",
            data=product_form(
                title="Gaming Mouse", description="High precision pointer"
            ),
            files=PRODUCT_IMAGE,
        )
        client.post(
            "/products",
            data=product_form(
                title="Keyboard", description="Includes a gaming mouse pad"
            ),
            files=PRODUCT_IMAGE,
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
            data=product_form(
                title="Desk Lamp", description="Warm light for reading sessions"
            ),
            files=PRODUCT_IMAGE,
        )

        response = client.get("/products", params={"search_query": "reading"})

        assert response.status_code == 200
        body = response.json()
        assert body["total"] == 1
        assert body["data"][0]["title"] == "Desk Lamp"

    def test_search_without_results_returns_empty_list(
        self, client: TestClient
    ) -> None:
        client.post("/products", data=product_form(), files=PRODUCT_IMAGE)

        response = client.get("/products", params={"search_query": "nonexistent"})

        assert response.status_code == 200
        body = response.json()
        assert body["total"] == 0
        assert body["data"] == []

    def test_filters_by_seller_id(self, client: TestClient) -> None:
        seller_a = str(uuid4())
        seller_b = str(uuid4())
        client.post(
            "/products",
            data=product_form(title="Seller A Product", seller_id=seller_a),
            files=PRODUCT_IMAGE,
        )
        client.post(
            "/products",
            data=product_form(title="Seller B Product", seller_id=seller_b),
            files=PRODUCT_IMAGE,
        )

        response = client.get("/products", params={"seller_id": seller_a})

        assert response.status_code == 200
        body = response.json()
        assert body["total"] == 1
        assert body["data"][0]["title"] == "Seller A Product"

    def test_lists_all_products_including_inactive(self, client: TestClient) -> None:
        client.post(
            "/products", data=product_form(title="Active Product"), files=PRODUCT_IMAGE
        )
        inactive = client.post(
            "/products",
            data=product_form(title="Inactive Product"),
            files=PRODUCT_IMAGE,
        )
        inactive_id = inactive.json()["data"]["id"]
        client.patch(f"/products/{inactive_id}", json={"status": "inactive"})

        response = client.get("/products", params={"include_inactive": "true"})

        assert response.status_code == 200
        assert response.json()["total"] == 2

    def test_lists_inactive_with_category_filter(self, client: TestClient) -> None:
        client.post(
            "/products",
            data=product_form(title="Active Peripheral", category="peripherals"),
            files=PRODUCT_IMAGE,
        )
        inactive = client.post(
            "/products",
            data=product_form(title="Inactive Peripheral", category="peripherals"),
            files=PRODUCT_IMAGE,
        )
        inactive_id = inactive.json()["data"]["id"]
        client.patch(f"/products/{inactive_id}", json={"status": "inactive"})

        response = client.get(
            "/products", params={"include_inactive": "true", "category": "peripherals"}
        )

        assert response.status_code == 200
        assert response.json()["total"] == 2

    def test_search_with_blank_query_returns_all_active(
        self, client: TestClient
    ) -> None:
        client.post(
            "/products", data=product_form(title="Product A"), files=PRODUCT_IMAGE
        )
        client.post(
            "/products", data=product_form(title="Product B"), files=PRODUCT_IMAGE
        )

        response = client.get("/products", params={"search_query": " "})

        assert response.status_code == 200
        assert response.json()["total"] == 2

    def test_search_hides_out_of_stock_products(self, client: TestClient) -> None:
        client.post(
            "/products",
            data=product_form(
                title="Available Camera", description="A camera for travel"
            ),
            files=PRODUCT_IMAGE,
        )
        client.post(
            "/products",
            data=product_form(
                title="Out of Stock Camera",
                description="A camera for travel",
                stock="0",
            ),
            files=PRODUCT_IMAGE,
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
            data=product_form(title="Rare Item", stock="0"),
            files=PRODUCT_IMAGE,
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


class TestUpdateProduct:
    """Partial update scenarios for products."""

    def test_updates_title(self, client: TestClient) -> None:
        create_response = client.post(
            "/products", data=product_form(), files=PRODUCT_IMAGE
        )
        product_id = create_response.json()["data"]["id"]

        response = client.patch(
            f"/products/{product_id}", json={"title": "Updated Keyboard"}
        )

        assert response.status_code == 200
        data = response.json()["data"]
        assert data["title"] == "Updated Keyboard"
        assert data["category"] == "peripherals"

    def test_updates_price_and_stock(self, client: TestClient) -> None:
        create_response = client.post(
            "/products", data=product_form(), files=PRODUCT_IMAGE
        )
        product_id = create_response.json()["data"]["id"]

        response = client.patch(
            f"/products/{product_id}", json={"price": 99.99, "stock": 3}
        )

        assert response.status_code == 200
        data = response.json()["data"]
        assert data["price"] == 99.99
        assert data["stock"] == 3

    def test_updates_category_normalizes_to_lowercase(self, client: TestClient) -> None:
        create_response = client.post(
            "/products", data=product_form(), files=PRODUCT_IMAGE
        )
        product_id = create_response.json()["data"]["id"]

        response = client.patch(
            f"/products/{product_id}", json={"category": "Office Supplies"}
        )

        assert response.status_code == 200
        assert response.json()["data"]["category"] == "office supplies"

    def test_deactivates_product(self, client: TestClient) -> None:
        create_response = client.post(
            "/products", data=product_form(), files=PRODUCT_IMAGE
        )
        product_id = create_response.json()["data"]["id"]

        response = client.patch(f"/products/{product_id}", json={"status": "inactive"})

        assert response.status_code == 200
        assert response.json()["data"]["status"] == "inactive"
        ids = [item["id"] for item in client.get("/products").json()["data"]]
        assert product_id not in ids

    def test_reactivates_product(self, client: TestClient) -> None:
        create_response = client.post(
            "/products", data=product_form(), files=PRODUCT_IMAGE
        )
        product_id = create_response.json()["data"]["id"]

        client.patch(f"/products/{product_id}", json={"status": "inactive"})
        response = client.patch(f"/products/{product_id}", json={"status": "active"})

        assert response.status_code == 200
        assert response.json()["data"]["status"] == "active"
        ids = [item["id"] for item in client.get("/products").json()["data"]]
        assert product_id in ids

    def test_returns_404_for_nonexistent_product(self, client: TestClient) -> None:
        response = client.patch(f"/products/{uuid4()}", json={"title": "Ghost"})

        assert response.status_code == 404
        assert response.json()["detail"] == "Product not found"

    def test_rejects_invalid_price(self, client: TestClient) -> None:
        create_response = client.post(
            "/products", data=product_form(), files=PRODUCT_IMAGE
        )
        product_id = create_response.json()["data"]["id"]

        response = client.patch(f"/products/{product_id}", json={"price": -10})

        assert response.status_code == 422

    def test_rejects_blank_title(self, client: TestClient) -> None:
        create_response = client.post(
            "/products", data=product_form(), files=PRODUCT_IMAGE
        )
        product_id = create_response.json()["data"]["id"]

        response = client.patch(f"/products/{product_id}", json={"title": "   "})

        assert response.status_code == 422

    def test_rejects_boolean_price(self, client: TestClient) -> None:
        create_response = client.post(
            "/products", data=product_form(), files=PRODUCT_IMAGE
        )
        product_id = create_response.json()["data"]["id"]

        response = client.patch(f"/products/{product_id}", json={"price": True})

        assert response.status_code == 422
