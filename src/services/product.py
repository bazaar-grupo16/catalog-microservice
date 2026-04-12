"""
Business logic for product catalog operations.
"""

from __future__ import annotations

import logging
from uuid import UUID, uuid4

from src.core.enums import ProductStatus
from src.core.utils import utc_now
from src.dtos import (
    AddImagesDTO,
    CreateProductDTO,
    DeleteImagesDTO,
    ImageFileDTO,
    ProductFilterDTO,
    ReorderImagesDTO,
    UpdateProductDTO,
)
from src.exceptions import (
    EmptyActiveProductImages,
    ImageValidationError,
    InvalidImageURLs,
    ProductNotFound,
)
from src.models import Product
from src.repositories import ProductRepository
from src.services.storage import (
    ALLOWED_MIME_TYPES,
    MAX_FILE_SIZE,
    StorageService,
)

logger = logging.getLogger(__name__)


class ProductService:
    """Service encapsulating business logic for product catalog operations."""

    def __init__(
        self,
        product_repository: ProductRepository,
        storage_service: StorageService | None = None,
    ) -> None:
        self.repository = product_repository
        self.storage = (
            storage_service if storage_service is not None else StorageService()
        )

    def create_product(
        self, dto: CreateProductDTO, images_dto: AddImagesDTO
    ) -> Product:
        """Create a product and upload its initial images atomically."""
        self._validate_files(images_dto.files)

        product = Product(**vars(dto))
        product = self.repository.create(product)

        urls: list[str] = []
        for f in images_dto.files:
            ext = self.storage.ext_for(f.content_type)
            key = f"products/{product.id}/{uuid4()}{ext}"
            urls.append(self.storage.upload(f.data, key, f.content_type))

        product.images = urls
        product.updated_at = utc_now()
        return self.repository.save(product)

    def get_products(self, filters: ProductFilterDTO) -> tuple[list[Product], int]:
        """Return a paginated product list following public visibility rules."""
        return self.repository.find_all(filters)

    def get_product(self, product_id: UUID) -> Product:
        """Fetch a single product details."""
        product = self.repository.find_by_id(product_id)
        if product is None:
            raise ProductNotFound(product_id)
        return product

    def delete_product(self, product_id: UUID) -> None:
        """Delete a product and attempt to remove its images from storage."""
        product = self.repository.find_by_id(product_id)
        if product is None:
            raise ProductNotFound(product_id)

        for url in list(product.images or []):
            try:
                self.storage.delete(self.storage.url_to_key(url))
            except Exception:
                logger.warning(
                    "Failed to delete image from storage: %s (product=%s)",
                    url,
                    product_id,
                )

        self.repository.delete(product)

    def update_product(self, product_id: UUID, dto: UpdateProductDTO) -> Product:
        """Partially update a product, only touching fields that were provided."""
        product = self.repository.find_by_id(product_id)
        if product is None:
            raise ProductNotFound(product_id)

        for field, value in vars(dto).items():
            if value is not None:
                setattr(product, field, value)

        return self.repository.save(product)

    def _validate_files(self, files: list[ImageFileDTO]) -> None:
        """Raise ImageValidationError if any file has an unsupported type or exceeds the size limit."""
        for f in files:
            if f.content_type not in ALLOWED_MIME_TYPES:
                raise ImageValidationError(
                    f"Unsupported file type '{f.content_type}'. "
                    "Only JPEG, PNG and WebP are allowed."
                )
            if len(f.data) > MAX_FILE_SIZE:
                raise ImageValidationError(
                    f"File exceeds the 10 MB size limit ({len(f.data)} bytes)."
                )

    def add_images(self, product_id: UUID, dto: AddImagesDTO) -> Product:
        """Validate, upload, and append images to a product."""
        product = self.repository.find_by_id(product_id)
        if product is None:
            raise ProductNotFound(product_id)

        self._validate_files(dto.files)

        new_urls: list[str] = []
        for f in dto.files:
            ext = self.storage.ext_for(f.content_type)
            key = f"products/{product_id}/{uuid4()}{ext}"
            url = self.storage.upload(f.data, key, f.content_type)
            new_urls.append(url)

        product.images = list(product.images or []) + new_urls
        product.updated_at = utc_now()
        return self.repository.save(product)

    def delete_images(self, product_id: UUID, dto: DeleteImagesDTO) -> Product:
        """Remove images from a product and delete them from storage."""
        product = self.repository.find_by_id(product_id)
        if product is None:
            raise ProductNotFound(product_id)

        current_set = set(product.images or [])
        invalid = [url for url in dto.urls if url not in current_set]
        if invalid:
            raise InvalidImageURLs(invalid)

        urls_to_remove = set(dto.urls)
        remaining = [url for url in (product.images or []) if url not in urls_to_remove]

        if product.status == ProductStatus.ACTIVE.value and not remaining:
            raise EmptyActiveProductImages()

        for url in dto.urls:
            self.storage.delete(self.storage.url_to_key(url))

        product.images = remaining
        product.updated_at = utc_now()
        return self.repository.save(product)

    def reorder_images(self, product_id: UUID, dto: ReorderImagesDTO) -> Product:
        """Replace the images array with a new ordering of the same URLs."""
        product = self.repository.find_by_id(product_id)
        if product is None:
            raise ProductNotFound(product_id)

        current = list(product.images or [])
        provided = dto.urls

        if sorted(provided) != sorted(current) or len(provided) != len(set(provided)):
            raise ImageValidationError(
                "The provided URLs must contain exactly the same set as the "
                "current images with no duplicates."
            )

        product.images = provided
        product.updated_at = utc_now()
        return self.repository.save(product)
