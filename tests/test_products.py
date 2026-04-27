"""
Integration tests for product CRUD endpoints.
"""

from __future__ import annotations

import time
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

    def test_creates_zero_stock_product_as_out_of_stock(
        self, client: TestClient
    ) -> None:
        response = client.post(
            "/products",
            data=product_form(title="Sold Out Listing", stock="0"),
            files=PRODUCT_IMAGE,
        )

        assert response.status_code == 201
        data = response.json()["data"]
        assert data["stock"] == 0
        assert data["status"] == "out_of_stock"

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

    def test_excludes_zero_stock_products_from_catalog(
        self, client: TestClient
    ) -> None:
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

    def test_search_excludes_out_of_stock_products(self, client: TestClient) -> None:
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
        titles = [item["title"] for item in body["data"]]
        assert "Available Camera" in titles
        assert "Out of Stock Camera" not in titles


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
        assert data["status"] == "out_of_stock"

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

    def test_updates_stock_and_status_simultaneously(self, client: TestClient) -> None:
        create_response = client.post(
            "/products", data=product_form(), files=PRODUCT_IMAGE
        )
        product_id = create_response.json()["data"]["id"]

        response = client.patch(
            f"/products/{product_id}", json={"stock": 0, "status": "inactive"}
        )

        assert response.status_code == 200
        data = response.json()["data"]
        assert data["status"] == "inactive"


class TestDeleteProduct:
    """Deletion scenarios for DELETE /products/{id}."""

    def test_returns_204(self, client: TestClient) -> None:
        create_response = client.post(
            "/products", data=product_form(), files=PRODUCT_IMAGE
        )
        product_id = create_response.json()["data"]["id"]

        response = client.delete(f"/products/{product_id}")

        assert response.status_code == 204
        assert response.content == b""

    def test_deleted_product_is_no_longer_accessible(self, client: TestClient) -> None:
        create_response = client.post(
            "/products", data=product_form(), files=PRODUCT_IMAGE
        )
        product_id = create_response.json()["data"]["id"]
        client.delete(f"/products/{product_id}")

        response = client.get(f"/products/{product_id}")

        assert response.status_code == 404

    def test_deleted_product_disappears_from_listing(self, client: TestClient) -> None:
        create_response = client.post(
            "/products", data=product_form(title="To Be Deleted"), files=PRODUCT_IMAGE
        )
        product_id = create_response.json()["data"]["id"]
        client.delete(f"/products/{product_id}")

        response = client.get("/products", params={"include_inactive": "true"})

        ids = [item["id"] for item in response.json()["data"]]
        assert product_id not in ids

    def test_calls_storage_delete_for_each_image(
        self, client: TestClient, storage_mock
    ) -> None:
        create_response = client.post(
            "/products", data=product_form(), files=PRODUCT_IMAGE
        )
        product_id = create_response.json()["data"]["id"]
        client.post(
            f"/products/{product_id}/images",
            files=[("files", ("extra.jpg", b"x" * 100, "image/jpeg"))],
        )
        storage_mock.delete.reset_mock()

        client.delete(f"/products/{product_id}")

        assert storage_mock.delete.call_count == 2

    def test_returns_404_for_nonexistent_product(self, client: TestClient) -> None:
        product_id = uuid4()

        response = client.delete(f"/products/{product_id}")

        assert response.status_code == 404
        body = response.json()
        assert body["type"] == "about:blank"
        assert body["title"] == "Not Found"
        assert body["status"] == 404
        assert body["detail"] == "Product not found"
        assert body["instance"] == f"/products/{product_id}"

    def test_continues_and_deletes_record_if_storage_fails(
        self, client: TestClient, storage_mock
    ) -> None:
        create_response = client.post(
            "/products", data=product_form(), files=PRODUCT_IMAGE
        )
        product_id = create_response.json()["data"]["id"]
        storage_mock.delete.side_effect = Exception("Spaces unavailable")

        response = client.delete(f"/products/{product_id}")

        assert response.status_code == 204
        assert client.get(f"/products/{product_id}").status_code == 404

    def test_deletes_product_with_no_images(self, client: TestClient) -> None:
        create_response = client.post(
            "/products", data=product_form(), files=PRODUCT_IMAGE
        )
        product_id = create_response.json()["data"]["id"]
        url = client.get(f"/products/{product_id}").json()["data"]["images"][0]
        client.patch(f"/products/{product_id}", json={"status": "inactive"})
        client.request("DELETE", f"/products/{product_id}/images", json={"urls": [url]})

        response = client.delete(f"/products/{product_id}")

        assert response.status_code == 204


class TestStockStatusCallback:
    """Internal stock-status callback scenarios."""

    def _create_product(self, client: TestClient) -> str:
        response = client.post("/products", data=product_form(), files=PRODUCT_IMAGE)
        assert response.status_code == 201
        return response.json()["data"]["id"]

    def test_has_stock_false_on_active_sets_out_of_stock(
        self, client: TestClient
    ) -> None:
        product_id = self._create_product(client)

        response = client.patch(
            f"/internal/products/{product_id}/stock-status",
            json={"has_stock": False},
        )

        assert response.status_code == 200
        assert response.json()["data"]["status"] == "out_of_stock"

    def test_has_stock_true_on_out_of_stock_sets_active(
        self, client: TestClient
    ) -> None:
        product_id = self._create_product(client)
        client.patch(
            f"/internal/products/{product_id}/stock-status",
            json={"has_stock": False},
        )

        response = client.patch(
            f"/internal/products/{product_id}/stock-status",
            json={"has_stock": True},
        )

        assert response.status_code == 200
        assert response.json()["data"]["status"] == "active"

    def test_callback_on_inactive_does_not_change_status(
        self, client: TestClient
    ) -> None:
        product_id = self._create_product(client)
        client.patch(f"/products/{product_id}", json={"status": "inactive"})

        response = client.patch(
            f"/internal/products/{product_id}/stock-status",
            json={"has_stock": False},
        )

        assert response.status_code == 200
        assert response.json()["data"]["status"] == "inactive"

    def test_callback_on_nonexistent_product_returns_404(
        self, client: TestClient
    ) -> None:
        product_id = str(uuid4())

        response = client.patch(
            f"/internal/products/{product_id}/stock-status",
            json={"has_stock": False},
        )

        assert response.status_code == 404
        body = response.json()
        assert body["type"] == "about:blank"
        assert body["title"] == "Not Found"
        assert body["status"] == 404

    def test_has_stock_true_on_already_active_product_is_noop(
        self, client: TestClient
    ) -> None:
        product_id = self._create_product(client)

        response = client.patch(
            f"/internal/products/{product_id}/stock-status",
            json={"has_stock": True},
        )

        assert response.status_code == 200
        assert response.json()["data"]["status"] == "active"

    def test_get_products_excludes_out_of_stock_by_default(
        self, client: TestClient
    ) -> None:
        product_id = self._create_product(client)
        client.patch(
            f"/internal/products/{product_id}/stock-status",
            json={"has_stock": False},
        )

        response = client.get("/products")

        assert response.status_code == 200
        ids = [p["id"] for p in response.json()["data"]]
        assert product_id not in ids

    def test_patch_stock_zero_on_active_sets_out_of_stock(
        self, client: TestClient
    ) -> None:
        product_id = self._create_product(client)

        response = client.patch(f"/products/{product_id}", json={"stock": 0})

        assert response.status_code == 200
        assert response.json()["data"]["status"] == "out_of_stock"

    def test_patch_stock_positive_on_out_of_stock_sets_active(
        self, client: TestClient
    ) -> None:
        product_id = self._create_product(client)
        client.patch(f"/products/{product_id}", json={"stock": 0})

        response = client.patch(f"/products/{product_id}", json={"stock": 5})

        assert response.status_code == 200
        assert response.json()["data"]["status"] == "active"


class TestSortProducts:
    """Sorting scenarios for GET /products."""

    def test_sort_by_price_ascending(self, client: TestClient) -> None:
        client.post("/products", data=product_form(title="Cheap", price="10.00"), files=PRODUCT_IMAGE)
        client.post("/products", data=product_form(title="Mid", price="50.00"), files=PRODUCT_IMAGE)
        client.post("/products", data=product_form(title="Expensive", price="200.00"), files=PRODUCT_IMAGE)

        response = client.get("/products", params={"sort_by": "price", "order": "asc"})

        assert response.status_code == 200
        prices = [item["price"] for item in response.json()["data"]]
        assert prices == sorted(prices)

    def test_sort_by_price_descending(self, client: TestClient) -> None:
        client.post("/products", data=product_form(title="Cheap", price="10.00"), files=PRODUCT_IMAGE)
        client.post("/products", data=product_form(title="Mid", price="50.00"), files=PRODUCT_IMAGE)
        client.post("/products", data=product_form(title="Expensive", price="200.00"), files=PRODUCT_IMAGE)

        response = client.get("/products", params={"sort_by": "price", "order": "desc"})

        assert response.status_code == 200
        prices = [item["price"] for item in response.json()["data"]]
        assert prices == sorted(prices, reverse=True)

    def test_sort_by_title_ascending(self, client: TestClient) -> None:
        client.post("/products", data=product_form(title="Zapato"), files=PRODUCT_IMAGE)
        client.post("/products", data=product_form(title="Abrigo"), files=PRODUCT_IMAGE)
        client.post("/products", data=product_form(title="Medias"), files=PRODUCT_IMAGE)

        response = client.get("/products", params={"sort_by": "title", "order": "asc"})

        assert response.status_code == 200
        titles = [item["title"] for item in response.json()["data"]]
        assert titles == sorted(titles)

    def test_sort_by_title_descending(self, client: TestClient) -> None:
        client.post("/products", data=product_form(title="Zapato"), files=PRODUCT_IMAGE)
        client.post("/products", data=product_form(title="Abrigo"), files=PRODUCT_IMAGE)
        client.post("/products", data=product_form(title="Medias"), files=PRODUCT_IMAGE)

        response = client.get("/products", params={"sort_by": "title", "order": "desc"})

        assert response.status_code == 200
        titles = [item["title"] for item in response.json()["data"]]
        assert titles == sorted(titles, reverse=True)

    def test_sort_by_created_at_ascending(self, client: TestClient) -> None:
        for title in ("First", "Second", "Third"):
            client.post("/products", data=product_form(title=title), files=PRODUCT_IMAGE)
            time.sleep(0.01)

        response = client.get("/products", params={"sort_by": "created_at", "order": "asc"})

        assert response.status_code == 200
        titles = [item["title"] for item in response.json()["data"]]
        assert titles == ["First", "Second", "Third"]

    def test_sort_by_created_at_descending(self, client: TestClient) -> None:
        for title in ("First", "Second", "Third"):
            client.post("/products", data=product_form(title=title), files=PRODUCT_IMAGE)
            time.sleep(0.01)

        response = client.get("/products", params={"sort_by": "created_at", "order": "desc"})

        assert response.status_code == 200
        titles = [item["title"] for item in response.json()["data"]]
        assert titles == ["Third", "Second", "First"]

    def test_sort_by_price_overrides_relevance_when_search_query_present(
        self, client: TestClient
    ) -> None:
        client.post(
            "/products",
            data=product_form(title="Gaming Mouse", price="80.00"),
            files=PRODUCT_IMAGE,
        )
        client.post(
            "/products",
            data=product_form(title="Keyboard", description="Includes a gaming mouse pad", price="30.00"),
            files=PRODUCT_IMAGE,
        )

        response = client.get(
            "/products",
            params={"search_query": "gaming mouse", "sort_by": "price", "order": "asc"},
        )

        assert response.status_code == 200
        body = response.json()
        assert body["total"] == 2
        prices = [item["price"] for item in body["data"]]
        assert prices == sorted(prices)

    def test_invalid_sort_by_returns_422(self, client: TestClient) -> None:
        response = client.get("/products", params={"sort_by": "invalid_field"})

        assert response.status_code == 422

    def test_invalid_order_returns_422(self, client: TestClient) -> None:
        response = client.get("/products", params={"sort_by": "price", "order": "random"})

        assert response.status_code == 422


class TestFilterByPrice:
    """Price range filter scenarios for GET /products."""

    def test_filters_by_min_price(self, client: TestClient) -> None:
        client.post("/products", data=product_form(title="Cheap", price="10.00"), files=PRODUCT_IMAGE)
        client.post("/products", data=product_form(title="Expensive", price="500.00"), files=PRODUCT_IMAGE)

        response = client.get("/products", params={"min_price": "100"})

        assert response.status_code == 200
        body = response.json()
        assert body["total"] == 1
        assert body["data"][0]["title"] == "Expensive"

    def test_filters_by_max_price(self, client: TestClient) -> None:
        client.post("/products", data=product_form(title="Cheap", price="10.00"), files=PRODUCT_IMAGE)
        client.post("/products", data=product_form(title="Expensive", price="500.00"), files=PRODUCT_IMAGE)

        response = client.get("/products", params={"max_price": "100"})

        assert response.status_code == 200
        body = response.json()
        assert body["total"] == 1
        assert body["data"][0]["title"] == "Cheap"

    def test_filters_by_price_range(self, client: TestClient) -> None:
        client.post("/products", data=product_form(title="Budget", price="15.00"), files=PRODUCT_IMAGE)
        client.post("/products", data=product_form(title="Mid", price="75.00"), files=PRODUCT_IMAGE)
        client.post("/products", data=product_form(title="Premium", price="400.00"), files=PRODUCT_IMAGE)

        response = client.get("/products", params={"min_price": "20", "max_price": "200"})

        assert response.status_code == 200
        body = response.json()
        assert body["total"] == 1
        assert body["data"][0]["title"] == "Mid"

    def test_price_boundaries_are_inclusive(self, client: TestClient) -> None:
        client.post("/products", data=product_form(title="Exact Min", price="50.00"), files=PRODUCT_IMAGE)
        client.post("/products", data=product_form(title="Exact Max", price="200.00"), files=PRODUCT_IMAGE)
        client.post("/products", data=product_form(title="Out", price="201.00"), files=PRODUCT_IMAGE)

        response = client.get("/products", params={"min_price": "50", "max_price": "200"})

        assert response.status_code == 200
        body = response.json()
        assert body["total"] == 2
        titles = {item["title"] for item in body["data"]}
        assert titles == {"Exact Min", "Exact Max"}

    def test_price_filter_combined_with_category(self, client: TestClient) -> None:
        client.post(
            "/products",
            data=product_form(title="Cheap Peripheral", price="20.00", category="peripherals"),
            files=PRODUCT_IMAGE,
        )
        client.post(
            "/products",
            data=product_form(title="Expensive Peripheral", price="300.00", category="peripherals"),
            files=PRODUCT_IMAGE,
        )
        client.post(
            "/products",
            data=product_form(title="Cheap Furniture", price="20.00", category="furniture"),
            files=PRODUCT_IMAGE,
        )

        response = client.get(
            "/products", params={"category": "peripherals", "max_price": "100"}
        )

        assert response.status_code == 200
        body = response.json()
        assert body["total"] == 1
        assert body["data"][0]["title"] == "Cheap Peripheral"

    def test_price_filter_combined_with_search_query(self, client: TestClient) -> None:
        client.post(
            "/products",
            data=product_form(title="Budget Laptop", price="400.00"),
            files=PRODUCT_IMAGE,
        )
        client.post(
            "/products",
            data=product_form(title="Premium Laptop", price="1500.00"),
            files=PRODUCT_IMAGE,
        )

        response = client.get(
            "/products", params={"search_query": "laptop", "max_price": "600"}
        )

        assert response.status_code == 200
        body = response.json()
        assert body["total"] == 1
        assert body["data"][0]["title"] == "Budget Laptop"

    def test_rejects_zero_min_price(self, client: TestClient) -> None:
        response = client.get("/products", params={"min_price": "0"})

        assert response.status_code == 422

    def test_rejects_negative_min_price(self, client: TestClient) -> None:
        response = client.get("/products", params={"min_price": "-5"})

        assert response.status_code == 422

    def test_rejects_zero_max_price(self, client: TestClient) -> None:
        response = client.get("/products", params={"max_price": "0"})

        assert response.status_code == 422

    def test_rejects_negative_max_price(self, client: TestClient) -> None:
        response = client.get("/products", params={"max_price": "-10"})

        assert response.status_code == 422


class TestFuzzySearch:
    """Búsqueda tolerante a errores tipográficos vía pg_trgm."""

    def test_fuzzy_finds_plural_variant(self, client: TestClient) -> None:
        """'hieleras' debe encontrar el producto cuyo título es 'hielera'."""
        client.post(
            "/products",
            data=product_form(title="hielera", description="Conserva bebidas frías"),
            files=PRODUCT_IMAGE,
        )

        response = client.get("/products", params={"search_query": "hieleras"})

        assert response.status_code == 200
        body = response.json()
        assert body["total"] == 1
        assert body["data"][0]["title"] == "hielera"

    def test_fuzzy_finds_missing_letter(self, client: TestClient) -> None:
        """'campra' debe encontrar 'campera' (letra faltante)."""
        client.post(
            "/products",
            data=product_form(title="campera", description="Abrigo de abrigo"),
            files=PRODUCT_IMAGE,
        )

        response = client.get("/products", params={"search_query": "campra"})

        assert response.status_code == 200
        body = response.json()
        assert body["total"] == 1
        assert body["data"][0]["title"] == "campera"

    def test_exact_match_ranked_above_fuzzy(self, client: TestClient) -> None:
        """Coincidencia exacta en título tiene mayor prioridad que coincidencia fuzzy."""
        client.post(
            "/products",
            data=product_form(title="campera", description="Abrigo clásico"),
            files=PRODUCT_IMAGE,
        )
        client.post(
            "/products",
            data=product_form(title="camperita", description="Versión reducida"),
            files=PRODUCT_IMAGE,
        )

        response = client.get("/products", params={"search_query": "campera"})

        assert response.status_code == 200
        body = response.json()
        assert body["total"] == 2
        assert body["data"][0]["title"] == "campera"

    def test_no_similar_query_returns_empty(self, client: TestClient) -> None:
        """Query sin ninguna similitud no debe devolver resultados."""
        client.post(
            "/products",
            data=product_form(title="teclado", description="Teclado mecánico"),
            files=PRODUCT_IMAGE,
        )

        response = client.get("/products", params={"search_query": "xyz123"})

        assert response.status_code == 200
        body = response.json()
        assert body["total"] == 0
        assert body["data"] == []
