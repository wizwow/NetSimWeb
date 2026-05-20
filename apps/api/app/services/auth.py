import uuid

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.core.auth import hash_password, verify_password
from app.models.user import User
from app.schemas.auth import AccountTier, AuthCredentialsSchema


class AuthService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def register(self, credentials: AuthCredentialsSchema) -> User:
        email = credentials.email.strip().lower()
        if "@" not in email:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Email must be valid",
            )
        result = await self.db.execute(select(User).where(User.email == email))
        if result.scalars().first():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="A user with this email already exists",
            )

        user = User(
            email=email,
            password_hash=hash_password(credentials.password),
            role="designer",
            account_tier="free",
        )
        self.db.add(user)
        await self.db.commit()
        await self.db.refresh(user)
        return user

    async def authenticate(self, credentials: AuthCredentialsSchema) -> User:
        email = credentials.email.strip().lower()
        result = await self.db.execute(select(User).where(User.email == email))
        user = result.scalars().first()
        if not user or not user.password_hash or not verify_password(
            credentials.password,
            user.password_hash,
        ):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password",
            )
        return user

    async def get_user(self, user_id: uuid.UUID) -> User | None:
        result = await self.db.execute(select(User).where(User.id == user_id))
        return result.scalars().first()

    async def get_or_create_dev_user(self, email: str) -> User:
        normalized = email.lower()
        result = await self.db.execute(select(User).where(User.email == normalized))
        user = result.scalars().first()
        if user:
            return user

        user = User(
            email=normalized,
            role="designer",
            account_tier="free",
            password_hash=None,
        )
        self.db.add(user)
        await self.db.commit()
        await self.db.refresh(user)
        return user


def user_to_read(user: User) -> dict:
    tier: AccountTier = user.account_tier if user.account_tier in {"free", "pro", "enterprise"} else "free"
    return {
        "id": user.id,
        "email": user.email,
        "role": user.role,
        "accountTier": tier,
    }
