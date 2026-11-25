
from datetime import datetime, timedelta, timezone
import hashlib

import jwt
from pwdlib import PasswordHash

from backend.app.core.config import settings

password_hash = PasswordHash.recommended()


def hash_password(password: str) -> str:
    return password_hash.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return password_hash.verify(plain_password, hashed_password)


def create_access_token(subject: str) -> str:
    expires_at = datetime.now(timezone.utc) + timedelta(
        minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
    )

    payload = {
        "sub": subject,
        "exp": expires_at
    }

    return jwt.encode(
        payload,
        settings.JWT_SECRET_KEY,
        algorithm="HS256"
    )


def password_fingerprint(hashed_password: str) -> str:
    """Short fingerprint of current password hash so reset tokens are single-use."""
    return hashlib.sha256(hashed_password.encode("utf-8")).hexdigest()[:16]


def create_password_reset_token(user_id: int, hashed_password: str) -> str:
    expires_at = datetime.now(timezone.utc) + timedelta(
        minutes=settings.PASSWORD_RESET_EXPIRE_MINUTES
    )

    payload = {
        "sub": str(user_id),
        "purpose": "password_reset",
        "fp": password_fingerprint(hashed_password),
        "exp": expires_at,
    }

    return jwt.encode(
        payload,
        settings.JWT_SECRET_KEY,
        algorithm="HS256"
    )


def verify_password_reset_token(token: str) -> tuple[int, str]:
    """Decode and validate a password reset JWT, returning (user_id, fingerprint)."""
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=["HS256"]
        )
        if payload.get("purpose") != "password_reset":
            raise ValueError("Invalid token purpose.")
        user_id = int(payload["sub"])
        fp = str(payload["fp"])
        return user_id, fp
    except (jwt.InvalidTokenError, KeyError, TypeError, ValueError) as exc:
        raise ValueError("Invalid or expired password reset token.") from exc
