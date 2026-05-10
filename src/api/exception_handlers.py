"""
FastAPI exception handlers for the catalog microservice.

All error responses follow RFC 7807 (application/problem+json).
"""

from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.exceptions import HTTPException
from fastapi.responses import JSONResponse

from src.exceptions import (
    EmptyActiveProductImages,
    ImageNotFound,
    ImageValidationError,
    InvalidImageURLs,
    ProductNotFound,
)

_HTTP_TITLES: dict[int, str] = {
    400: "Bad Request",
    401: "Unauthorized",
    403: "Forbidden",
    404: "Not Found",
    405: "Method Not Allowed",
    409: "Conflict",
    422: "Unprocessable Entity",
    500: "Internal Server Error",
}


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

    @app.exception_handler(HTTPException)
    async def http_exception_handler(
        request: Request, exc: HTTPException
    ) -> JSONResponse:
        title = _HTTP_TITLES.get(exc.status_code, "Error")
        return _problem(request, exc.status_code, title, exc.detail or "")

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
            "A product must retain at least one image",
        )

    @app.exception_handler(ImageNotFound)
    async def image_not_found_handler(
        request: Request, exc: ImageNotFound
    ) -> JSONResponse:
        keys_str = ", ".join(exc.keys)
        return _problem(
            request,
            404,
            "Not Found",
            f"Image not found in product: {keys_str}",
        )
