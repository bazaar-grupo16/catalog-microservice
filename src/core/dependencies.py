"""
FastAPI dependencies for dependency injection.

Add shared dependencies here (e.g. database sessions, auth context).
"""

from collections.abc import Generator
from typing import Annotated
from uuid import UUID

from fastapi import Depends, Header
from fastapi.exceptions import HTTPException
from sqlalchemy.orm import Session

from src.core.database import SessionLocal


def _get_db() -> Generator[Session, None, None]:
    """Yield a SQLAlchemy session and ensure it is closed afterwards."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_current_user_id(
    x_user_id: str | None = Header(default=None),
) -> UUID:
    if x_user_id is None:
        raise HTTPException(status_code=401, detail="Missing X-User-ID header")
    try:
        return UUID(x_user_id)
    except ValueError:
        raise HTTPException(status_code=401, detail="Invalid X-User-ID header")


# Re-usable annotated dependencies for route signatures.
DbSession = Annotated[Session, Depends(_get_db)]
UserID = Annotated[UUID, Depends(get_current_user_id)]
