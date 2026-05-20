import uuid
from typing import Literal

from pydantic import BaseModel, Field


AccountTier = Literal["free", "pro", "enterprise"]


class UserReadSchema(BaseModel):
    id: uuid.UUID
    email: str
    role: str = "designer"
    accountTier: AccountTier = "free"


class AuthCredentialsSchema(BaseModel):
    email: str = Field(min_length=3, max_length=254)
    password: str = Field(min_length=8, max_length=128)


class AuthTokenSchema(BaseModel):
    accessToken: str
    tokenType: str = "bearer"
    user: UserReadSchema
