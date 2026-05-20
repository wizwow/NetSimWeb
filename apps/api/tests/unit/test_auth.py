import uuid

import pytest
from fastapi import HTTPException

from app.core import auth
from app.core.auth import (
    create_access_token,
    hash_password,
    parse_dev_bearer_token,
    verify_access_token,
    verify_password,
)
from app.services.simulation import SimulationService
from app.services.topology import TopologyService


def test_password_hash_round_trip_and_rejects_wrong_password():
    password_hash = hash_password("correct-horse")

    assert verify_password("correct-horse", password_hash) is True
    assert verify_password("wrong-horse", password_hash) is False


def test_jwt_round_trip_contains_user_claims():
    user_id = uuid.uuid4()
    token = create_access_token(user_id, "teacher@example.com")

    payload = verify_access_token(token)

    assert payload["sub"] == str(user_id)
    assert payload["email"] == "teacher@example.com"


def test_jwt_rejects_tampered_token():
    token = create_access_token(uuid.uuid4(), "teacher@example.com")
    header, payload, signature = token.split(".")
    replacement_payload = "e30"
    tampered = f"{header}.{replacement_payload}.{signature}"
    assert payload != replacement_payload

    with pytest.raises(HTTPException):
        verify_access_token(tampered)


def test_jwt_rejects_expired_token(monkeypatch):
    monkeypatch.setattr(auth, "ACCESS_TOKEN_EXPIRE_MINUTES", -1)
    token = create_access_token(uuid.uuid4(), "teacher@example.com")

    with pytest.raises(HTTPException, match="401"):
        verify_access_token(token)


def test_dev_auth_requires_explicit_flag(monkeypatch):
    monkeypatch.setattr(auth, "DEV_AUTH_ENABLED", False)
    with pytest.raises(HTTPException):
        parse_dev_bearer_token(None)

    monkeypatch.setattr(auth, "DEV_AUTH_ENABLED", True)
    assert parse_dev_bearer_token(None) == auth.DEV_USER_EMAIL
    assert parse_dev_bearer_token("Bearer dev:teacher@example.com") == "teacher@example.com"


def test_topology_service_filters_by_owner_id():
    owner_id = uuid.uuid4()
    service = TopologyService(db=None, owner_id=owner_id)

    query_text = str(service._owned_query())

    assert "topologies.owner_id" in query_text


def test_simulation_service_carries_owner_id():
    owner_id = uuid.uuid4()
    service = SimulationService(db=None, engine=None, owner_id=owner_id)

    assert service.owner_id == owner_id
