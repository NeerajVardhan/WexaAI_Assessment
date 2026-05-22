import hmac
import secrets
from datetime import UTC, datetime, timedelta
from typing import Any

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
JWT_ALGORITHM = "HS256"


def utcnow() -> datetime:
    return datetime.now(UTC)


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    return pwd_context.verify(password, password_hash)


def create_access_token(subject: str, org_id: str, role: str) -> str:
    expires = utcnow() + timedelta(minutes=settings.access_token_expire_minutes)
    payload: dict[str, Any] = {
        "sub": subject,
        "org": org_id,
        "role": role,
        "type": "access",
        "exp": expires,
        "iat": utcnow(),
    }
    return jwt.encode(payload, settings.secret_key, algorithm=JWT_ALGORITHM)


def decode_token(token: str, expected_type: str = "access") -> dict[str, Any]:
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[JWT_ALGORITHM])
    except JWTError as exc:
        raise ValueError("Invalid token") from exc
    if payload.get("type") != expected_type:
        raise ValueError("Invalid token type")
    return payload


def new_secret(prefix: str = "wx") -> str:
    return f"{prefix}_{secrets.token_urlsafe(32)}"


def hash_secret(secret: str) -> str:
    return hmac.new(settings.secret_key.encode(), secret.encode(), "sha256").hexdigest()


def constant_time_equals(left: str, right: str) -> bool:
    return hmac.compare_digest(left, right)

