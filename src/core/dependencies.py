"""
FastAPI dependencies for dependency injection.

Add shared dependencies here (e.g. database sessions, auth context).
"""

from collections.abc import Generator
from typing import Annotated
from uuid import UUID

import jwt
from fastapi import Depends, HTTPException, Request
from sqlalchemy.orm import Session

from src.core.config import get_settings
from src.core.database import SessionLocal


def _get_db() -> Generator[Session, None, None]:
    """Yield a SQLAlchemy session and ensure it is closed afterwards."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _get_current_user_id(request: Request) -> UUID:
    x_user_id = request.headers.get("X-User-ID")
    if x_user_id is not None:
        try:
            return UUID(x_user_id)
        except ValueError:
            raise HTTPException(status_code=401, detail="Invalid X-User-ID header")

    settings = get_settings()
    auth_header = request.headers.get("Authorization")

    if auth_header is None:
        raise HTTPException(status_code=401, detail="Missing Authorization header")

    parts = auth_header.split(" ", 1)
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise HTTPException(
            status_code=401, detail="Invalid Authorization header format"
        )

    token = parts[1]

    try:
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.JWT_ALGORITHM]
        )
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token has expired")
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Token is invalid")

    if payload.get("type") != "access":
        raise HTTPException(status_code=401, detail="Token is invalid")

    user_id_claim = payload.get("sub")
    try:
        return UUID(str(user_id_claim))
    except (ValueError, AttributeError):
        raise HTTPException(status_code=401, detail="Token is invalid")


# Re-usable annotated dependencies for route signatures.
DbSession = Annotated[Session, Depends(_get_db)]
UserID = Annotated[UUID, Depends(_get_current_user_id)]
