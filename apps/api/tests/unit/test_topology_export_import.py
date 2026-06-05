import uuid
from datetime import datetime, timezone
from types import SimpleNamespace

from fastapi.testclient import TestClient

from app.main import app
from app.routers.topology import get_topology_service
from app.schemas.topology import TopologyExportSchema


class FakeTopologyService:
    async def export_topology(self, topology_id: uuid.UUID):
        return TopologyExportSchema(
            topologyId=topology_id,
            name="Exported Topology",
            abstractionLevel="logical",
            status="running",
            exportedAt=datetime.now(timezone.utc).isoformat(),
            nodes=[
                {
                    "id": "r1",
                    "label": "R1",
                    "position": {"x": 0, "y": 0},
                    "baseType": "router",
                    "tags": [],
                }
            ],
            edges=[],
        )

    async def import_topology(self, import_data):
        return SimpleNamespace(
            id=uuid.uuid4(),
            name=import_data.name,
            description=import_data.description,
            abstraction_level=import_data.abstractionLevel,
            status="draft",
            owner_id=None,
            engine_topo_id=None,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            graph_json={
                "nodes": [node.model_dump() for node in import_data.nodes],
                "edges": [edge.model_dump() for edge in import_data.edges],
            },
        )


def test_export_topology_route_returns_netsimflow_document():
    app.dependency_overrides[get_topology_service] = lambda: FakeTopologyService()
    client = TestClient(app)
    topology_id = uuid.uuid4()

    try:
        response = client.get(f"/api/v1/topology/{topology_id}/export")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    body = response.json()
    assert body["exportFormat"] == "netsimflow-v1"
    assert body["topologyId"] == str(topology_id)
    assert body["nodes"][0]["id"] == "r1"


def test_import_topology_route_creates_draft_topology():
    app.dependency_overrides[get_topology_service] = lambda: FakeTopologyService()
    client = TestClient(app)

    try:
        response = client.post(
            "/api/v1/topology/import",
            json={
                "exportFormat": "netsimflow-v1",
                "name": "Imported Topology",
                "abstractionLevel": "logical",
                "status": "running",
                "nodes": [
                    {
                        "id": "r1",
                        "label": "R1",
                        "position": {"x": 0, "y": 0},
                        "baseType": "router",
                        "tags": [],
                    }
                ],
                "edges": [],
            },
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 201
    body = response.json()
    assert body["name"] == "Imported Topology"
    assert body["status"] == "draft"
    assert body["nodes"][0]["id"] == "r1"
