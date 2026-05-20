import base64
import hashlib
import hmac
import json
import os
import secrets
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db


DEV_USER_EMAIL = os.getenv("DEV_AUTH_EMAIL", "dev@netsimflow.local")
DEV_AUTH_ENABLED = os.getenv("DEV_AUTH_ENABLED", "false").lower() in {"1", "true", "yes"}
SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-change-in-prod")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "480"))
JWT_ALGORITHM = "HS256"


@dataclass(frozen=True)
class CurrentUser:
    id: uuid.UUID
    email: str
    role: str
    account_tier: str = "free"


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 390_000)
    return f"pbkdf2_sha256${_b64url_encode(salt)}${_b64url_encode(digest)}"


def verify_password(password: str, password_hash: str) -> bool:
    try:
        scheme, salt_b64, digest_b64 = password_hash.split("$", 2)
    except ValueError:
        return False
    if scheme != "pbkdf2_sha256":
        return False

    salt = _b64url_decode(salt_b64)
    expected = _b64url_decode(digest_b64)
    actual = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 390_000)
    return hmac.compare_digest(actual, expected)


def create_access_token(user_id: uuid.UUID, email: str) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user_id),
        "email": email.lower(),
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)).timestamp()),
    }
    return _encode_jwt(payload)


def verify_access_token(token: str) -> dict[str, Any]:
    try:
        header_b64, payload_b64, signature_b64 = token.split(".", 2)
    except ValueError as exc:
        raise _credentials_error("Invalid access token") from exc

    signed = f"{header_b64}.{payload_b64}".encode("ascii")
    expected_signature = _sign(signed)
    try:
        supplied_signature = _b64url_decode(signature_b64)
    except ValueError as exc:
        raise _credentials_error("Invalid access token") from exc
    if not hmac.compare_digest(expected_signature, supplied_signature):
        raise _credentials_error("Invalid access token")

    try:
        header = json.loads(_b64url_decode(header_b64))
        payload = json.loads(_b64url_decode(payload_b64))
    except (json.JSONDecodeError, ValueError) as exc:
        raise _credentials_error("Invalid access token") from exc

    if header.get("alg") != JWT_ALGORITHM or header.get("typ") != "JWT":
        raise _credentials_error("Invalid access token")

    exp = payload.get("exp")
    if not isinstance(exp, int) or exp < int(datetime.now(timezone.utc).timestamp()):
        raise _credentials_error("Access token expired")

    if not payload.get("sub"):
        raise _credentials_error("Invalid access token")
    return payload


def parse_dev_bearer_token(authorization: str | None) -> str:
    if not DEV_AUTH_ENABLED:
        raise _credentials_error("Development auth bypass is disabled")
    if not authorization:
        return DEV_USER_EMAIL

    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise _credentials_error("Expected Authorization: Bearer dev:<email>")
    prefix, _, email = token.partition(":")
    if prefix != "dev" or "@" not in email:
        raise _credentials_error("Invalid development auth token")
    return email.strip().lower()


async def get_current_user(
    authorization: str | None = Header(default=None),
    db: AsyncSession = Depends(get_db),
) -> CurrentUser:
    from app.services.auth import AuthService

    service = AuthService(db)
    if DEV_AUTH_ENABLED and (not authorization or authorization.startswith("Bearer dev:")):
        user = await service.get_or_create_dev_user(parse_dev_bearer_token(authorization))
        return CurrentUser(
            id=user.id,
            email=user.email,
            role=user.role,
            account_tier=user.account_tier,
        )

    if not authorization:
        raise _credentials_error("Missing Authorization header")

    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise _credentials_error("Expected Authorization: Bearer <token>")

    payload = verify_access_token(token)
    try:
        user_id = uuid.UUID(str(payload["sub"]))
    except (KeyError, ValueError) as exc:
        raise _credentials_error("Invalid access token") from exc

    user = await service.get_user(user_id)
    if not user:
        raise _credentials_error("User not found")
    return CurrentUser(
        id=user.id,
        email=user.email,
        role=user.role,
        account_tier=user.account_tier,
    )


def _encode_jwt(payload: dict[str, Any]) -> str:
    header = {"alg": JWT_ALGORITHM, "typ": "JWT"}
    header_b64 = _b64url_encode(json.dumps(header, separators=(",", ":")).encode("utf-8"))
    payload_b64 = _b64url_encode(json.dumps(payload, separators=(",", ":")).encode("utf-8"))
    signature = _b64url_encode(_sign(f"{header_b64}.{payload_b64}".encode("ascii")))
    return f"{header_b64}.{payload_b64}.{signature}"


def _sign(message: bytes) -> bytes:
    return hmac.new(SECRET_KEY.encode("utf-8"), message, hashlib.sha256).digest()


def _b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _b64url_decode(data: str) -> bytes:
    padding = "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode(f"{data}{padding}".encode("ascii"))


def _credentials_error(detail: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detail,
        headers={"WWW-Authenticate": "Bearer"},
    )
