"""ORM model for the product status change audit log."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import DateTime, String
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import Uuid

from src.core.database import Base
from src.core.utils import utc_now


class ProductStatusHistory(Base):
    __tablename__ = "product_status_history"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    product_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False, index=True)
    previous_state: Mapped[str | None] = mapped_column(String(20), nullable=True)
    new_state: Mapped[str] = mapped_column(String(20), nullable=False)
    changed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )
    changed_by: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True), nullable=True)
    changed_by_role: Mapped[str | None] = mapped_column(String(20), nullable=True)
