import uuid
from datetime import datetime, timezone
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from app.core.exceptions import NotFoundError
from app.main import app
from app.routers.topology import get_topology_service
from app.services.report import generate_markdown_report
from app.services.templates import TemplateService


def topology_model(name="OSPF 3 Sites", nodes=None, edges=None):
    return SimpleNamespace(
        id=uuid.uuid4(),
        name=name,
        description=None,
        abstraction_level="logical",
        status="draft",
        graph_json={"nodes": nodes or [], "edges": edges or []},
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )


def test_markdown_report_contains_professional_sections_for_ospf_template():
    topology = TemplateService().instantiate("ospf-3-sites")
    topo_model = topology_model(nodes=[node.model_dump() for node in topology.nodes], edges=[edge.model_dump() for edge in topology.edges])

    report = generate_markdown_report(topo_model)

    assert "# NetSim-Flow Report: OSPF 3 Sites" in report
    assert "## Metadata" in report
    assert "## Node Inventory" in report
    assert "## Interface / IP Table" in report
    assert "## Link Table" in report
    assert "## Routing Summary" in report
    assert "OSPF" in report or "ospf" in report
    assert "10.0.1.0/30" in report
    assert "site-hq:eth0" in report


def test_blank_topology_markdown_report_is_valid():
    topology = TemplateService().instantiate("blank")
    topo_model = topology_model(name="Blank", nodes=topology.nodes, edges=topology.edges)

    report = generate_markdown_report(topo_model)

    assert "# NetSim-Flow Report: Blank" in report
    assert "- **Nodes:** 0" in report
    assert "- **Links:** 0" in report
    assert "_No nodes in this topology._" in report
    assert "_No links in this topology._" in report


class FakeReportService:
    async def export_report_markdown(self, topology_id):
        return f"# Report\n\nTopology: {topology_id}\n"


class MissingReportService:
    async def export_report_markdown(self, topology_id):
        raise NotFoundError("Topology", str(topology_id))


def test_report_endpoint_returns_markdown():
    app.dependency_overrides[get_topology_service] = lambda: FakeReportService()
    client = TestClient(app)
    topology_id = uuid.uuid4()

    try:
        response = client.get(f"/api/v1/topology/{topology_id}/report.md")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/markdown")
    assert response.text.startswith("# Report")
    assert str(topology_id) in response.text


def test_report_endpoint_returns_404_for_missing_topology():
    app.dependency_overrides[get_topology_service] = lambda: MissingReportService()
    client = TestClient(app)

    try:
        response = client.get(f"/api/v1/topology/{uuid.uuid4()}/report.md")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 404
