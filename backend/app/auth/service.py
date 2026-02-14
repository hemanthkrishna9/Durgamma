"""Authentication service — JWT-based auth for the dashboard.

Simple JWT authentication with user registration and login.
Passwords are hashed with bcrypt. Tokens expire after 24 hours.
"""

import hashlib
import hmac
import logging
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.db.database import get_db

logger = logging.getLogger(__name__)

# JWT settings
JWT_SECRET = settings.anthropic_api_key or secrets.token_hex(32)
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_HOURS = 24

security = HTTPBearer(auto_error=False)


def _hash_password(password: str, salt: str | None = None) -> tuple[str, str]:
    """Hash a password with a salt using PBKDF2."""
    if salt is None:
        salt = secrets.token_hex(16)
    hashed = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 100000)
    return hashed.hex(), salt


def _verify_password(password: str, hashed: str, salt: str) -> bool:
    """Verify a password against its hash."""
    computed, _ = _hash_password(password, salt)
    return hmac.compare_digest(computed, hashed)


def create_token(user_id: str, email: str, role: str = "user") -> str:
    """Create a JWT token."""
    now = datetime.now(timezone.utc)
    payload = {
        "sub": user_id,
        "email": email,
        "role": role,
        "iat": now,
        "exp": now + timedelta(hours=JWT_EXPIRATION_HOURS),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def decode_token(token: str) -> dict[str, Any]:
    """Decode and validate a JWT token."""
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token has expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
) -> dict[str, Any] | None:
    """Extract the current user from the JWT token.

    Returns None if no token is provided (allows unauthenticated access).
    Use require_auth for endpoints that must be authenticated.
    """
    if credentials is None:
        return None
    return decode_token(credentials.credentials)


async def require_auth(
    user: dict[str, Any] | None = Depends(get_current_user),
) -> dict[str, Any]:
    """Require authentication for an endpoint."""
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


async def require_admin(
    user: dict[str, Any] = Depends(require_auth),
) -> dict[str, Any]:
    """Require admin role for an endpoint."""
    if user.get("role") != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )
    return user
