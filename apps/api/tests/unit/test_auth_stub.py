import uuid

import pytest
from fastapi import HTTPException

from app.core.auth import DEV_USER_EMAIL, parse_stub_bearer_token
from app.services.simulation import SimulationService
from app.services.topology import TopologyService


def test_stub_auth_uses_dev_user_without_header():
    assert parse_stub_bearer_token(None) == DEV_USER_EMAIL


def test_stub_auth_accepts_dev_bearer_email():
    assert parse_stub_bearer_token("Bearer dev:teacher@example.com") == "teacher@example.com"


def test_stub_auth_rejects_invalid_token():
    with pytest.raises(HTTPException):
        parse_stub_bearer_token("Bearer nope")


def test_topology_service_filters_by_owner_id():
    owner_id = uuid.uuid4()
    service = TopologyService(db=None, owner_id=owner_id)

    query_text = str(service._owned_query())

    assert "topologies.owner_id" in query_text


def test_simulation_service_carries_owner_id():
    owner_id = uuid.uuid4()
    service = SimulationService(db=None, engine=None, owner_id=owner_id)

    assert service.owner_id == owner_id
