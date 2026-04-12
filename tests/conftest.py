"""
Shared pytest fixtures for the test suite.

Tests run against a **real PostgreSQL** database provided by
``docker-compose.test.yml``.  Connection details come from the
same environment variables the application uses in production
(DB_HOST, DB_PORT, DB_USER, DB_PASSWORD, DB_NAME).

Storage (DigitalOcean Spaces) is **mocked** in image tests — no real
uploads are made.  Dummy SPACES_* values are set below so that
``get_settings()`` passes validation before any module is imported.
"""

import os
from unittest.mock import MagicMock, patch

# Set dummy Spaces credentials before any src module is imported.
# get_settings() validates all fields at first call (triggered by the
# database module import below), so these must be in place beforehand.
# docker-compose.test.yml also sets them for CI runs.
for _k, _v in [
    ("SPACES_KEY", "test-key"),
    ("SPACES_SECRET", "test-secret"),
    ("SPACES_BUCKET", "test-bucket"),
    ("SPACES_REGION", "nyc3"),
    ("SPACES_ENDPOINT", "https://nyc3.digitaloceanspaces.com"),
    ("SPACES_CDN_ENDPOINT", "https://bazaar-media.nyc3.cdn.digitaloceanspaces.com"),
]:
    os.environ.setdefault(_k, _v)

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from src.core.database import Base, engine
from src.main import app


@pytest.fixture(scope="session", autouse=True)
def _setup_database():
    """Create all tables before the session and tear them down after."""
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture(autouse=True)
def _clean_database() -> None:
    """Truncate domain tables between tests to keep cases isolated."""
    with engine.begin() as connection:
        connection.execute(text("TRUNCATE TABLE products RESTART IDENTITY CASCADE"))
    yield


@pytest.fixture()
def client() -> TestClient:
    """Return a ``TestClient`` bound to the FastAPI application."""
    return TestClient(app)


# ── Storage mock ──────────────────────────────────────────────────────────────
# autouse=True so every test gets this automatically.
# POST /products now requires images, so all product-creation calls need
# StorageService intercepted — even tests that aren't about images.

_CDN_BASE = "https://bazaar-media.nyc3.cdn.digitaloceanspaces.com"
_MIME_TO_EXT = {"image/jpeg": ".jpg", "image/png": ".png", "image/webp": ".webp"}

# Default image file included in every POST /products call.
PRODUCT_IMAGE = [("files", ("photo.jpg", b"x" * 100, "image/jpeg"))]


@pytest.fixture(autouse=True)
def storage_mock():
    """Patch StorageService so no real boto3/Spaces calls are made."""
    mock = MagicMock()
    mock.upload.side_effect = lambda data, key, ct: f"{_CDN_BASE}/{key}"
    mock.delete.return_value = None
    mock.url_to_key.side_effect = lambda url: url.removeprefix(f"{_CDN_BASE}/")
    mock.ext_for.side_effect = lambda ct: _MIME_TO_EXT[ct]

    with patch("src.services.product.StorageService", return_value=mock):
        yield mock
