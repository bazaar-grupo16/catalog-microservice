"""
Bazaar Microservice — Application entry-point.

Creates the FastAPI application, registers routers, and configures
structured logging.  Database tables are created on startup via the
ORM metadata (suitable for development; use Alembic migrations in
production).
"""

import logging
from contextlib import asynccontextmanager
from collections.abc import AsyncIterator

from fastapi import FastAPI

from src.api.exception_handlers import register_exception_handlers
from src.api.health import router as health_router
from src.api.routers.internal import router as internal_router
from src.api.routers.my_products import router as my_products_router
from src.api.routers.product import router as products_router
from src.core.config import get_settings
from src.core.database import Base, engine, setup_search_extensions, wait_for_db
from src.core.logging import setup_logging
from src.core.observability import CorrelationIdMiddleware
from src.models import Product, ProductStatusHistory  # noqa: F401


settings = get_settings()
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    """Application startup / shutdown lifecycle hook."""
    setup_logging()
    logger.info("Starting %s", settings.APP_NAME)
    # Wait for the database before creating tables.
    wait_for_db()
    # Create tables (dev convenience — use Alembic in production).
    Base.metadata.create_all(bind=engine)
    setup_search_extensions()
    yield
    logger.info("Shutting down %s", settings.APP_NAME)


app = FastAPI(
    title=settings.APP_NAME,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)
app.add_middleware(CorrelationIdMiddleware)

# ── Routers ──────────────────────────────────────────
app.include_router(health_router)
app.include_router(products_router)
app.include_router(my_products_router)
app.include_router(internal_router)


# ── Exception handlers ────────────────────────────────
register_exception_handlers(app)
