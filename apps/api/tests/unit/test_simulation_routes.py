import uuid
from types import SimpleNamespace

from fastapi.testclient import TestClient

from app.main import app
from app.routers.simulation import get_simulation_service
from app.routers.templates import get_template_service
from app.schemas.topology import ProbeResultSchema, TemplateSummarySchema, TopologyBase


class FakeTemplateService:
    def list_templates(self):
        return [
            TemplateSummarySchema(
                id="blank",
                name="Blank",
                description="Empty topology",
                tags=["blank"],
            )
        ]

    def instantiate(self, template_id: str):
        return TopologyBase(
            name="Blank",
            description=f"Template {template_id}",
            status="draft",
            nodes=[],
            edges=[],
        )


class FakeSimulationService:
    def __init__(self) -> None:
        self.probes = []
        self.faults = []

    async def run_probe(self, topology_id: uuid.UUID, probe):
        self.probes.append((topology_id, probe))
        return ProbeResultSchema(success=True, output=f"Reply from {probe.targetIp}: 3ms", rttMs=3)

    async def inject_fault(self, topology_id: uuid.UUID, fault):
        self.faults.append((topology_id, fault))
        return SimpleNamespace(status="running")


def test_templates_routes_return_list_and_instantiated_topology():
    app.dependency_overrides[get_template_service] = lambda: FakeTemplateService()
    client = TestClient(app)

    try:
        list_response = client.get("/api/v1/templates/")
        instantiate_response = client.post("/api/v1/templates/blank/instantiate")
    finally:
        app.dependency_overrides.clear()

    assert list_response.status_code == 200
    assert list_response.json()[0]["id"] == "blank"
    assert instantiate_response.status_code == 200
    assert instantiate_response.json()["name"] == "Blank"


def test_probe_route_uses_simulation_service_contract():
    fake_service = FakeSimulationService()
    app.dependency_overrides[get_simulation_service] = lambda: fake_service
    client = TestClient(app)
    topology_id = uuid.uuid4()

    try:
        response = client.post(
            f"/api/v1/topology/{topology_id}/probe",
            json={"sourceNodeId": "r1", "targetIp": "10.255.0.2", "probeType": "ping"},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["success"] is True
    assert fake_service.probes[0][1].sourceNodeId == "r1"


def test_fault_route_uses_simulation_service_contract():
    fake_service = FakeSimulationService()
    app.dependency_overrides[get_simulation_service] = lambda: fake_service
    client = TestClient(app)
    topology_id = uuid.uuid4()

    try:
        response = client.post(
            f"/api/v1/topology/{topology_id}/fault",
            json={"linkId": "link-1", "faultType": "link-down"},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "topology_status": "running"}
    assert fake_service.faults[0][1].linkId == "link-1"
