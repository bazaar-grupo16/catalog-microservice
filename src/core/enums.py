"""
Shared enumeration types for the catalog microservice.
"""

from enum import StrEnum


class ProductStatus(StrEnum):
    """Allowed publication states for products."""

    ACTIVE = "active"
    INACTIVE = "inactive"
