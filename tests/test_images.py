"""
Integration tests for product image management endpoints.

POST   /products/{id}/images               — upload one or more images
DELETE /products/{id}/images               — remove images by URL
DELETE /products/{product_id}/images/bulk  — remove images by storage key (bulk)
DELETE /products/{product_id}/images/{key} — remove a single image by storage key
PATCH  /products/{id}/images/order         — reorder images

StorageService is patched globally via the autouse fixture in conftest.py
— no real boto3/Spaces calls are made.
"""

from __future__ import annotations

from uuid import uuid4

from fastapi.testclient import TestClient

from tests.conftest import PRODUCT_IMAGE, _CDN_BASE


# ── Helpers ───────────────────────────────────────────────────────────────────


def image_file(
    name: str = "photo.jpg",
    mime: str = "image/jpeg",
    size: int = 512,
) -> tuple:
    """Build a multipart file tuple for TestClient."""
    return ("files", (name, b"x" * size, mime))


# ── Fixtures ──────────────────────────────────────────────────────────────────


def _make_product(client: TestClient) -> str:
    """Create a product and return its ID string."""
    from uuid import uuid4

    response = client.post(
        "/products",
        data={
            "title": "Camera",
            "description": "High resolution camera",
            "price": "299.99",
            "stock": "5",
            "category": "Electronics",
            "seller_id": str(uuid4()),
        },
        files=PRODUCT_IMAGE,
    )
    assert response.status_code == 201
    return response.json()["data"]["id"]


# ── POST /products/{id}/images ────────────────────────────────────────────────


class TestAddImages:
    def test_appends_single_image(self, client: TestClient) -> None:
        pid = _make_product(client)

        response = client.post(f"/products/{pid}/images", files=[image_file()])

        assert response.status_code == 200
        images = response.json()["data"]["images"]
        # First image comes from product creation, second from this upload
        assert len(images) == 2
        assert all(img.startswith(_CDN_BASE) for img in images)

    def test_appends_multiple_images_preserving_order(self, client: TestClient) -> None:
        pid = _make_product(client)

        response = client.post(
            f"/products/{pid}/images",
            files=[image_file("a.jpg"), image_file("b.png", "image/png")],
        )

        assert response.status_code == 200
        assert len(response.json()["data"]["images"]) == 3  # 1 from creation + 2

    def test_appends_to_existing_images(self, client: TestClient) -> None:
        pid = _make_product(client)
        client.post(f"/products/{pid}/images", files=[image_file("extra.jpg")])

        response = client.post(
            f"/products/{pid}/images", files=[image_file("more.jpg")]
        )

        assert response.status_code == 200
        assert len(response.json()["data"]["images"]) == 3  # 1 + 1 + 1

    def test_images_appear_in_get_product(self, client: TestClient) -> None:
        pid = _make_product(client)
        client.post(f"/products/{pid}/images", files=[image_file()])

        response = client.get(f"/products/{pid}")

        assert len(response.json()["data"]["images"]) == 2

    def test_images_appear_in_list_products(self, client: TestClient) -> None:
        pid = _make_product(client)

        response = client.get("/products")

        product = next(p for p in response.json()["data"] if p["id"] == pid)
        assert len(product["images"]) == 1  # image from creation

    def test_product_creation_requires_at_least_one_image(
        self, client: TestClient
    ) -> None:
        from uuid import uuid4

        response = client.post(
            "/products",
            data={
                "title": "No Image Product",
                "description": "Missing images",
                "price": "10.00",
                "stock": "1",
                "category": "test",
                "seller_id": str(uuid4()),
            },
            # no files parameter
        )
        assert response.status_code == 422

    def test_returns_404_for_nonexistent_product(self, client: TestClient) -> None:
        response = client.post(
            f"/products/{uuid4()}/images",
            files=[image_file()],
        )

        assert response.status_code == 404
        assert response.json()["type"] == "about:blank"

    def test_rejects_unsupported_mime_type(self, client: TestClient) -> None:
        pid = _make_product(client)

        response = client.post(
            f"/products/{pid}/images",
            files=[("files", ("doc.pdf", b"pdf content", "application/pdf"))],
        )

        assert response.status_code == 400
        body = response.json()
        assert body["type"] == "about:blank"
        assert body["status"] == 400

    def test_rejects_oversized_file(self, client: TestClient) -> None:
        pid = _make_product(client)
        big = b"x" * (10 * 1024 * 1024 + 1)

        response = client.post(
            f"/products/{pid}/images",
            files=[("files", ("big.jpg", big, "image/jpeg"))],
        )

        assert response.status_code == 400

    def test_rejects_entire_batch_if_any_file_is_invalid(
        self, client: TestClient, storage_mock
    ) -> None:
        pid = _make_product(client)
        images_before = client.get(f"/products/{pid}").json()["data"]["images"]
        storage_mock.upload.reset_mock()

        response = client.post(
            f"/products/{pid}/images",
            files=[
                image_file("valid.jpg"),
                ("files", ("bad.txt", b"text", "text/plain")),
            ],
        )

        assert response.status_code == 400
        storage_mock.upload.assert_not_called()
        assert client.get(f"/products/{pid}").json()["data"]["images"] == images_before

    def test_updates_updated_at(self, client: TestClient) -> None:
        pid = _make_product(client)
        before = client.get(f"/products/{pid}").json()["data"]["updatedAt"]

        client.post(f"/products/{pid}/images", files=[image_file()])

        after = client.get(f"/products/{pid}").json()["data"]["updatedAt"]
        assert after >= before


# ── DELETE /products/{id}/images ─────────────────────────────────────────────


class TestDeleteImages:
    def test_removes_image_from_array(self, client: TestClient) -> None:
        pid = _make_product(client)
        images = client.get(f"/products/{pid}").json()["data"]["images"]
        client.patch(f"/products/{pid}", json={"status": "inactive"})

        response = client.request(
            "DELETE", f"/products/{pid}/images", json={"urls": images}
        )

        assert response.status_code == 200
        assert response.json()["data"]["images"] == []

    def test_removes_subset_and_preserves_order(self, client: TestClient) -> None:
        pid = _make_product(client)
        extra = client.post(
            f"/products/{pid}/images",
            files=[image_file("a.jpg"), image_file("b.jpg")],
        ).json()["data"]["images"]
        # extra now has 3 urls: [creation_img, a.jpg, b.jpg]

        response = client.request(
            "DELETE", f"/products/{pid}/images", json={"urls": [extra[1]]}
        )

        assert response.status_code == 200
        remaining = response.json()["data"]["images"]
        assert remaining == [extra[0], extra[2]]

    def test_calls_storage_delete_for_each_url(
        self, client: TestClient, storage_mock
    ) -> None:
        pid = _make_product(client)
        images = client.post(
            f"/products/{pid}/images",
            files=[image_file("a.jpg"), image_file("b.jpg")],
        ).json()["data"]["images"]
        storage_mock.delete.reset_mock()

        client.request(
            "DELETE", f"/products/{pid}/images", json={"urls": [images[0], images[2]]}
        )

        assert storage_mock.delete.call_count == 2

    def test_returns_404_for_nonexistent_product(self, client: TestClient) -> None:
        response = client.request(
            "DELETE",
            f"/products/{uuid4()}/images",
            json={"urls": [f"{_CDN_BASE}/products/fake/img.jpg"]},
        )

        assert response.status_code == 404

    def test_returns_400_for_url_not_in_product(self, client: TestClient) -> None:
        pid = _make_product(client)

        response = client.request(
            "DELETE",
            f"/products/{pid}/images",
            json={"urls": [f"{_CDN_BASE}/products/{pid}/ghost.jpg"]},
        )

        assert response.status_code == 400
        body = response.json()
        assert body["type"] == "about:blank"
        assert body["status"] == 400

    def test_returns_409_when_last_image_removed_from_active_product(
        self, client: TestClient
    ) -> None:
        pid = _make_product(client)
        url = client.get(f"/products/{pid}").json()["data"]["images"][0]

        response = client.request(
            "DELETE", f"/products/{pid}/images", json={"urls": [url]}
        )

        assert response.status_code == 409
        body = response.json()
        assert body["type"] == "about:blank"
        assert body["status"] == 409

    def test_allows_removing_all_images_from_inactive_product(
        self, client: TestClient
    ) -> None:
        pid = _make_product(client)
        urls = client.get(f"/products/{pid}").json()["data"]["images"]
        client.patch(f"/products/{pid}", json={"status": "inactive"})

        response = client.request(
            "DELETE", f"/products/{pid}/images", json={"urls": urls}
        )

        assert response.status_code == 200
        assert response.json()["data"]["images"] == []

    def test_updates_updated_at(self, client: TestClient) -> None:
        pid = _make_product(client)
        urls = client.get(f"/products/{pid}").json()["data"]["images"]
        client.patch(f"/products/{pid}", json={"status": "inactive"})
        before = client.get(f"/products/{pid}").json()["data"]["updatedAt"]

        client.request("DELETE", f"/products/{pid}/images", json={"urls": urls})

        after = client.get(f"/products/{pid}").json()["data"]["updatedAt"]
        assert after >= before


# ── DELETE /products/{product_id}/images/{image_key} ─────────────────────────


class TestDeleteImageByKey:
    def test_deletes_image_and_returns_updated_product(self, client: TestClient) -> None:
        pid = _make_product(client)
        images = client.get(f"/products/{pid}").json()["data"]["images"]
        client.patch(f"/products/{pid}", json={"status": "inactive"})
        image_key = images[0].split("/")[-1]

        response = client.delete(f"/products/{pid}/images/{image_key}")

        assert response.status_code == 200
        assert images[0] not in response.json()["data"]["images"]

    def test_calls_storage_delete(self, client: TestClient, storage_mock) -> None:
        pid = _make_product(client)
        images = client.get(f"/products/{pid}").json()["data"]["images"]
        client.patch(f"/products/{pid}", json={"status": "inactive"})
        storage_mock.delete.reset_mock()
        image_key = images[0].split("/")[-1]

        client.delete(f"/products/{pid}/images/{image_key}")

        assert storage_mock.delete.call_count == 1

    def test_returns_404_for_nonexistent_product(self, client: TestClient) -> None:
        response = client.delete(f"/products/{uuid4()}/images/ghost.jpg")

        assert response.status_code == 404
        assert response.json()["type"] == "about:blank"

    def test_returns_404_for_key_not_in_product(self, client: TestClient) -> None:
        pid = _make_product(client)

        response = client.delete(f"/products/{pid}/images/nonexistent.jpg")

        assert response.status_code == 404
        body = response.json()
        assert body["type"] == "about:blank"
        assert body["status"] == 404

    def test_returns_409_when_last_image_removed_from_active_product(
        self, client: TestClient
    ) -> None:
        pid = _make_product(client)
        images = client.get(f"/products/{pid}").json()["data"]["images"]
        image_key = images[0].split("/")[-1]

        response = client.delete(f"/products/{pid}/images/{image_key}")

        assert response.status_code == 409
        body = response.json()
        assert body["type"] == "about:blank"
        assert body["status"] == 409

    def test_allows_removing_last_image_from_inactive_product(
        self, client: TestClient
    ) -> None:
        pid = _make_product(client)
        images = client.get(f"/products/{pid}").json()["data"]["images"]
        client.patch(f"/products/{pid}", json={"status": "inactive"})
        image_key = images[0].split("/")[-1]

        response = client.delete(f"/products/{pid}/images/{image_key}")

        assert response.status_code == 200
        assert response.json()["data"]["images"] == []


# ── DELETE /products/{product_id}/images/bulk ─────────────────────────────────


class TestBulkDeleteImagesByKeys:
    def test_deletes_multiple_images(self, client: TestClient) -> None:
        pid = _make_product(client)
        images = client.post(
            f"/products/{pid}/images",
            files=[image_file("a.jpg"), image_file("b.jpg")],
        ).json()["data"]["images"]
        # images = [creation_img, a.jpg, b.jpg]
        keys = [images[1].split("/")[-1], images[2].split("/")[-1]]

        response = client.request(
            "DELETE", f"/products/{pid}/images/bulk", json={"image_keys": keys}
        )

        assert response.status_code == 200
        remaining = response.json()["data"]["images"]
        assert len(remaining) == 1
        assert images[0] in remaining
        assert images[1] not in remaining
        assert images[2] not in remaining

    def test_calls_storage_delete_for_each_key(
        self, client: TestClient, storage_mock
    ) -> None:
        pid = _make_product(client)
        images = client.post(
            f"/products/{pid}/images",
            files=[image_file("a.jpg"), image_file("b.jpg")],
        ).json()["data"]["images"]
        keys = [images[1].split("/")[-1], images[2].split("/")[-1]]
        storage_mock.delete.reset_mock()

        client.request(
            "DELETE", f"/products/{pid}/images/bulk", json={"image_keys": keys}
        )

        assert storage_mock.delete.call_count == 2

    def test_returns_404_for_nonexistent_product(self, client: TestClient) -> None:
        response = client.request(
            "DELETE",
            f"/products/{uuid4()}/images/bulk",
            json={"image_keys": ["ghost.jpg"]},
        )

        assert response.status_code == 404
        assert response.json()["type"] == "about:blank"

    def test_returns_404_when_any_key_not_in_product(self, client: TestClient) -> None:
        pid = _make_product(client)

        response = client.request(
            "DELETE",
            f"/products/{pid}/images/bulk",
            json={"image_keys": ["nonexistent.jpg"]},
        )

        assert response.status_code == 404
        body = response.json()
        assert body["type"] == "about:blank"
        assert body["status"] == 404
        assert "nonexistent.jpg" in body["detail"]

    def test_returns_409_when_last_image_removed_from_active_product(
        self, client: TestClient
    ) -> None:
        pid = _make_product(client)
        images = client.get(f"/products/{pid}").json()["data"]["images"]
        image_key = images[0].split("/")[-1]

        response = client.request(
            "DELETE", f"/products/{pid}/images/bulk", json={"image_keys": [image_key]}
        )

        assert response.status_code == 409
        body = response.json()
        assert body["type"] == "about:blank"
        assert body["status"] == 409

    def test_allows_removing_all_images_from_inactive_product(
        self, client: TestClient
    ) -> None:
        pid = _make_product(client)
        images = client.get(f"/products/{pid}").json()["data"]["images"]
        client.patch(f"/products/{pid}", json={"status": "inactive"})
        keys = [img.split("/")[-1] for img in images]

        response = client.request(
            "DELETE", f"/products/{pid}/images/bulk", json={"image_keys": keys}
        )

        assert response.status_code == 200
        assert response.json()["data"]["images"] == []


# ── PATCH /products/{id}/images/order ────────────────────────────────────────


class TestReorderImages:
    def test_reorders_images(self, client: TestClient) -> None:
        pid = _make_product(client)
        images = client.post(
            f"/products/{pid}/images",
            files=[image_file("a.jpg"), image_file("b.jpg")],
        ).json()["data"]["images"]
        new_order = [images[2], images[0], images[1]]

        response = client.patch(
            f"/products/{pid}/images/order", json={"urls": new_order}
        )

        assert response.status_code == 200
        assert response.json()["data"]["images"] == new_order

    def test_returns_404_for_nonexistent_product(self, client: TestClient) -> None:
        response = client.patch(
            f"/products/{uuid4()}/images/order",
            json={"urls": [f"{_CDN_BASE}/products/fake/img.jpg"]},
        )

        assert response.status_code == 404

    def test_returns_400_for_missing_url(self, client: TestClient) -> None:
        pid = _make_product(client)
        images = client.post(
            f"/products/{pid}/images",
            files=[image_file("a.jpg"), image_file("b.jpg")],
        ).json()["data"]["images"]

        response = client.patch(
            f"/products/{pid}/images/order", json={"urls": [images[0]]}
        )

        assert response.status_code == 400

    def test_returns_400_for_extra_url(self, client: TestClient) -> None:
        pid = _make_product(client)
        images = client.get(f"/products/{pid}").json()["data"]["images"]
        extra = f"{_CDN_BASE}/products/{pid}/extra.jpg"

        response = client.patch(
            f"/products/{pid}/images/order",
            json={"urls": [images[0], extra]},
        )

        assert response.status_code == 400

    def test_returns_400_for_duplicate_urls(self, client: TestClient) -> None:
        pid = _make_product(client)
        images = client.post(
            f"/products/{pid}/images",
            files=[image_file("a.jpg"), image_file("b.jpg")],
        ).json()["data"]["images"]

        response = client.patch(
            f"/products/{pid}/images/order",
            json={"urls": [images[0], images[0]]},
        )

        assert response.status_code == 400

    def test_updates_updated_at(self, client: TestClient) -> None:
        pid = _make_product(client)
        images = client.post(
            f"/products/{pid}/images",
            files=[image_file("a.jpg"), image_file("b.jpg")],
        ).json()["data"]["images"]
        before = client.get(f"/products/{pid}").json()["data"]["updatedAt"]

        client.patch(
            f"/products/{pid}/images/order",
            json={"urls": [images[2], images[1], images[0]]},
        )

        after = client.get(f"/products/{pid}").json()["data"]["updatedAt"]
        assert after >= before
