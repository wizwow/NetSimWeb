import os
import uuid
from dataclasses import dataclass

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.core.database import get_db
from app.models.user import User


DEV_USER_EMAIL = os.getenv("DEV_AUTH_EMAIL", "dev@netsimflow.local")


@dataclass(frozen=True)
class CurrentUser:
    id: uuid.UUID
    email: str
    role: str


def parse_stub_bearer_token(authorization: str | None) -> str:
    """Return an email from the temporary auth token format.

    This is intentionally tiny until real JWT signing/login is added.
    Accepted format: ``Authorization: Bearer dev:user@example.com``.
    Missing auth falls back to the local dev user so current manual testing still works.
    """

    if not authorization:
        return DEV_USER_EMAIL

    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Expected Authorization: Bearer dev:<email>",
        )
    prefix, _, email = token.partition(":")
    if prefix != "dev" or "@" not in email:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid auth stub token",
        )
    return email.strip().lower()


async def get_current_user(
    authorization: str | None = Header(default=None),
    db: AsyncSession = Depends(get_db),
) -> CurrentUser:
    email = parse_stub_bearer_token(authorization)
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalars().first()
    if not user:
        user = User(email=email, role="designer")
        db.add(user)
        await db.commit()
        await db.refresh(user)

    return CurrentUser(id=user.id, email=user.email, role=user.role)
