"""
FastAPI exception handlers for the catalog microservice.

All error responses follow RFC 7807 (application/problem+json).
"""

from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from src.exceptions import (
    EmptyActiveProductImages,
    ImageValidationError,
    InvalidImageURLs,
    ProductNotFound,
)


def _problem(
    request: Request,
    status: int,
    title: str,
    detail: str,
) -> JSONResponse:
    return JSONResponse(
        status_code=status,
        content={
            "type": "about:blank",
            "title": title,
            "status": status,
            "detail": detail,
            "instance": request.url.path,
        },
        media_type="application/problem+json",
    )


def register_exception_handlers(app: FastAPI) -> None:
    """Attach all domain exception handlers to *app*."""

    @app.exception_handler(ProductNotFound)
    async def product_not_found_handler(
        request: Request, exc: ProductNotFound
    ) -> JSONResponse:
        return _problem(request, 404, "Not Found", "Product not found")

    @app.exception_handler(ImageValidationError)
    async def image_validation_error_handler(
        request: Request, exc: ImageValidationError
    ) -> JSONResponse:
        return _problem(request, 400, "Bad Request", exc.detail)

    @app.exception_handler(InvalidImageURLs)
    async def invalid_image_urls_handler(
        request: Request, exc: InvalidImageURLs
    ) -> JSONResponse:
        return _problem(
            request,
            400,
            "Bad Request",
            "One or more image URLs are not associated with this product",
        )

    @app.exception_handler(EmptyActiveProductImages)
    async def empty_active_product_images_handler(
        request: Request, exc: EmptyActiveProductImages
    ) -> JSONResponse:
        return _problem(
            request,
            409,
            "Conflict",
            "An active product must retain at least one image",
        )
