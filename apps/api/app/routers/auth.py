from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import CurrentUser, create_access_token, get_current_user
from app.core.database import get_db
from app.schemas.auth import AuthCredentialsSchema, AuthTokenSchema, UserReadSchema
from app.services.auth import AuthService, user_to_read


router = APIRouter(prefix="/auth", tags=["Auth"])


def get_auth_service(db: AsyncSession = Depends(get_db)) -> AuthService:
    return AuthService(db)


@router.post("/register", response_model=AuthTokenSchema)
async def register(
    credentials: AuthCredentialsSchema,
    svc: AuthService = Depends(get_auth_service),
) -> dict:
    user = await svc.register(credentials)
    return {
        "accessToken": create_access_token(user.id, user.email),
        "user": user_to_read(user),
    }


@router.post("/login", response_model=AuthTokenSchema)
async def login(
    credentials: AuthCredentialsSchema,
    svc: AuthService = Depends(get_auth_service),
) -> dict:
    user = await svc.authenticate(credentials)
    return {
        "accessToken": create_access_token(user.id, user.email),
        "user": user_to_read(user),
    }


@router.get("/me", response_model=UserReadSchema)
async def me(user: CurrentUser = Depends(get_current_user)) -> dict:
    return {
        "id": user.id,
        "email": user.email,
        "role": user.role,
        "accountTier": user.account_tier,
    }
