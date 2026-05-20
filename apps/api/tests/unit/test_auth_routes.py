import uuid
from types import SimpleNamespace

from fastapi import HTTPException
from fastapi.testclient import TestClient

from app.core.auth import CurrentUser, get_current_user
from app.main import app
from app.routers.auth import get_auth_service
from app.schemas.auth import AuthCredentialsSchema


class FakeAuthService:
    async def register(self, credentials: AuthCredentialsSchema):
        return SimpleNamespace(
            id=uuid.uuid4(),
            email=credentials.email,
            role="designer",
            account_tier="free",
        )

    async def authenticate(self, credentials: AuthCredentialsSchema):
        if credentials.password != "valid-pass":
            raise HTTPException(status_code=401, detail="Invalid email or password")
        return SimpleNamespace(
            id=uuid.uuid4(),
            email=credentials.email,
            role="designer",
            account_tier="free",
        )


def test_register_route_returns_user_token_and_tier():
    app.dependency_overrides[get_auth_service] = lambda: FakeAuthService()
    client = TestClient(app)

    try:
        response = client.post(
            "/api/v1/auth/register",
            json={"email": "teacher@example.com", "password": "valid-pass"},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["accessToken"]
    assert response.json()["user"]["accountTier"] == "free"


def test_login_route_rejects_bad_credentials():
    app.dependency_overrides[get_auth_service] = lambda: FakeAuthService()
    client = TestClient(app)

    try:
        response = client.post(
            "/api/v1/auth/login",
            json={"email": "teacher@example.com", "password": "wrong-pass"},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 401


def test_me_route_returns_current_user_tier():
    user_id = uuid.uuid4()
    app.dependency_overrides[get_current_user] = lambda: CurrentUser(
        id=user_id,
        email="teacher@example.com",
        role="designer",
        account_tier="pro",
    )
    client = TestClient(app)

    try:
        response = client.get("/api/v1/auth/me")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json() == {
        "id": str(user_id),
        "email": "teacher@example.com",
        "role": "designer",
        "accountTier": "pro",
    }
