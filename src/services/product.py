"""
Business logic for product catalog operations.
"""

from __future__ import annotations

import logging
from uuid import UUID, uuid4

from src.core.config import get_settings
from src.core.enums import ProductStatus
from src.core.utils import utc_now
from src.dtos import (
    AddImagesDTO,
    BulkDeleteImagesByKeysDTO,
    CreateProductDTO,
    DeleteImageByKeyDTO,
    DeleteImagesDTO,
    ImageFileDTO,
    ProductFilterDTO,
    ReorderImagesDTO,
    UpdateProductDTO,
)
from src.exceptions import (
    EmptyActiveProductImages,
    ImageNotFound,
    ImageValidationError,
    InvalidImageURLs,
    ProductNotFound,
)
from src.models import Product
from src.repositories import ProductRepository
from src.services.inventory import InventoryService
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
        storage_service: StorageService,
        inventory_service: InventoryService,
    ) -> None:
        self.repository = product_repository
        self.storage = storage_service
        self.inventory = inventory_service

    def create_product(
        self, dto: CreateProductDTO, images_dto: AddImagesDTO
    ) -> Product:
        """Create a product, upload its initial images, and register it in inventory."""
        self._validate_files(images_dto.files)

        product = Product(
            title=dto.title,
            description=dto.description,
            price=dto.price,
            category=dto.category,
            seller_id=dto.seller_id,
            status=(
                ProductStatus.OUT_OF_STOCK.value
                if dto.stock == 0
                else ProductStatus.ACTIVE.value
            ),
        )
        product = self.repository.create(product)

        urls: list[str] = []
        for f in images_dto.files:
            ext = self.storage.ext_for(f.content_type)
            key = f"products/{product.id}/{uuid4()}{ext}"
            urls.append(self.storage.upload(f.data, key, f.content_type))

        product.images = urls
        product.updated_at = utc_now()
        product = self.repository.save(product)

        self.inventory.create_product_stock(product.id, dto.stock)
        return self._enrich_stock(product)

    def get_products(self, filters: ProductFilterDTO) -> tuple[list[Product], int]:
        """Return a paginated product list. Stock is enriched from inventory for display."""
        products, total = self.repository.find_all(filters)
        if products:
            stocks = self.inventory.get_stocks([p.id for p in products])
            for product in products:
                product.stock = stocks.get(product.id, 0)
        return products, total

    def get_product(self, product_id: UUID) -> Product:
        """Fetch a single product, enriching its stock from inventory."""
        product = self.repository.find_by_id(product_id)
        if product is None:
            raise ProductNotFound(product_id)
        return self._enrich_stock(product)

    def get_share_link(self, product_id: UUID) -> str:
        """Return a shareable public URL for an active product."""
        product = self.repository.find_by_id(product_id)
        if product is None:
            raise ProductNotFound(product_id)
        base = get_settings().PUBLIC_APP_BASE_URL.rstrip("/")
        return f"{base}/products/{product_id}"

    def delete_product(self, product_id: UUID) -> None:
        """Delete a product, remove its images from storage, and deregister it from inventory."""
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
        self.inventory.delete_product_stock(product_id)

    def update_product(self, product_id: UUID, dto: UpdateProductDTO) -> Product:
        """Partially update a product, delegating stock changes to inventory."""
        product = self.repository.find_by_id(product_id)
        if product is None:
            raise ProductNotFound(product_id)

        for field, value in vars(dto).items():
            if field == "stock" or value is None:
                continue
            setattr(product, field, value)

        if dto.stock is not None:
            self.inventory.update_product_stock(product_id, dto.stock)
            if dto.status is None:
                if dto.stock == 0 and product.status == ProductStatus.ACTIVE.value:
                    product.status = ProductStatus.OUT_OF_STOCK.value
                elif (
                    dto.stock > 0 and product.status == ProductStatus.OUT_OF_STOCK.value
                ):
                    product.status = ProductStatus.ACTIVE.value

        product = self.repository.save(product)
        return self._enrich_stock(product)

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

    def _enrich_stock(self, product: Product) -> Product:
        """Set product.stock from inventory (non-mapped attribute for response serialization)."""
        product.stock = self.inventory.get_product_stock(product.id)
        return product

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
        return self._enrich_stock(self.repository.save(product))

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
        self._ensure_product_keeps_images(remaining)

        for url in dto.urls:
            self.storage.delete(self.storage.url_to_key(url))

        product.images = remaining
        product.updated_at = utc_now()
        return self._enrich_stock(self.repository.save(product))

    def delete_image_by_key(
        self, product_id: UUID, dto: DeleteImageByKeyDTO
    ) -> Product:
        """Remove a single image by its storage key (filename) from a product."""
        product = self.repository.find_by_id(product_id)
        if product is None:
            raise ProductNotFound(product_id)

        matching_url = next(
            (
                url
                for url in (product.images or [])
                if url.endswith(f"/{dto.image_key}")
            ),
            None,
        )
        if matching_url is None:
            raise ImageNotFound([dto.image_key])

        remaining = [url for url in (product.images or []) if url != matching_url]
        self._ensure_product_keeps_images(remaining)

        self.storage.delete(self.storage.url_to_key(matching_url))
        product.images = remaining
        product.updated_at = utc_now()
        return self._enrich_stock(self.repository.save(product))

    def bulk_delete_images_by_keys(
        self, product_id: UUID, dto: BulkDeleteImagesByKeysDTO
    ) -> Product:
        """Remove multiple images by their storage keys from a product."""
        product = self.repository.find_by_id(product_id)
        if product is None:
            raise ProductNotFound(product_id)

        current_images = list(product.images or [])
        keys_to_urls: dict[str, str | None] = {
            key: next((url for url in current_images if url.endswith(f"/{key}")), None)
            for key in dto.image_keys
        }
        missing = [key for key, url in keys_to_urls.items() if url is None]
        if missing:
            raise ImageNotFound(missing)

        urls_to_remove = {url for url in keys_to_urls.values() if url is not None}
        remaining = [url for url in current_images if url not in urls_to_remove]
        self._ensure_product_keeps_images(remaining)

        for url in urls_to_remove:
            self.storage.delete(self.storage.url_to_key(url))

        product.images = remaining
        product.updated_at = utc_now()
        return self._enrich_stock(self.repository.save(product))

    def update_stock_status(self, product_id: UUID, has_stock: bool) -> Product:
        """Update product status based on inventory availability (called by inventory service)."""
        product = self.repository.find_by_id(product_id)
        if product is None:
            raise ProductNotFound(product_id)

        if product.status == ProductStatus.INACTIVE.value:
            return self._enrich_stock(product)

        if not has_stock and product.status == ProductStatus.ACTIVE.value:
            product.status = ProductStatus.OUT_OF_STOCK.value
            product.updated_at = utc_now()
            product = self.repository.save(product)
        elif has_stock and product.status == ProductStatus.OUT_OF_STOCK.value:
            product.status = ProductStatus.ACTIVE.value
            product.updated_at = utc_now()
            product = self.repository.save(product)

        return self._enrich_stock(product)

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
        return self._enrich_stock(self.repository.save(product))

    def _ensure_product_keeps_images(self, remaining: list[str]) -> None:
        """Reject operations that would leave a product without any images."""
        if not remaining:
            raise EmptyActiveProductImages()
