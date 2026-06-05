import uuid
from datetime import datetime, timezone
from types import SimpleNamespace

from fastapi.testclient import TestClient

from app.core.exceptions import NotFoundError
from app.main import app
from app.routers.topology import get_topology_service
from app.services.report import (
    _topology_png_data_uri,
    _topology_svg,
    generate_doc_report,
    generate_markdown_report,
    generate_pdf_report,
)
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

    assert "# Octet Report: OSPF 3 Sites" in report
    assert "## Metadata" in report
    assert "## Topology Overview" in report
    assert "<svg" in report
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

    assert "# Octet Report: Blank" in report
    assert "- **Nodes:** 0" in report
    assert "- **Links:** 0" in report
    assert "_No nodes in this topology._" in report
    assert "_No links in this topology._" in report


def test_pdf_report_is_valid_pdf_bytes():
    topology = TemplateService().instantiate("ospf-3-sites")
    topo_model = topology_model(nodes=[node.model_dump() for node in topology.nodes], edges=[edge.model_dump() for edge in topology.edges])

    pdf = generate_pdf_report(topo_model)

    assert pdf.startswith(b"%PDF-1.")
    assert len(pdf) > 1000
    assert b"# Octet Report" not in pdf
    assert b"| Label | Type |" not in pdf
    assert b"%%EOF" in pdf[-32:]
    assert len(pdf) > 20_000


def test_doc_report_is_word_compatible_html_bytes():
    topology = TemplateService().instantiate("ospf-3-sites")
    topo_model = topology_model(nodes=[node.model_dump() for node in topology.nodes], edges=[edge.model_dump() for edge in topology.edges])

    doc = generate_doc_report(topo_model)

    assert doc.startswith(b"<!doctype html>")
    assert b"Octet Report" in doc
    assert b"10.0.1.0/30" in doc
    assert b"data:image/png;base64," in doc
    assert b"<svg" not in doc
    assert b"<table>" in doc
    assert b"<pre>" not in doc
    assert b"# Octet Report" not in doc
    assert b"| Label | Type |" not in doc


def test_topology_svg_is_rasterized_for_rendered_reports():
    topology = TemplateService().instantiate("ospf-3-sites")

    svg = _topology_svg(topology)
    image_uri = _topology_png_data_uri(svg)

    assert svg.startswith('<svg xmlns="http://www.w3.org/2000/svg"')
    assert 'width="760"' in svg
    assert 'height="420"' in svg
    assert image_uri.startswith("data:image/png;base64,")
    assert len(image_uri) > 1000


class FakeReportService:
    async def export_report_markdown(self, topology_id):
        return f"# Report\n\nTopology: {topology_id}\n"

    async def export_report_pdf(self, topology_id):
        return b"%PDF-1.4\nfake\n%%EOF\n"

    async def export_report_doc(self, topology_id):
        return b"<!doctype html><html><body>Report</body></html>"


class MissingReportService:
    async def export_report_markdown(self, topology_id):
        raise NotFoundError("Topology", str(topology_id))

    async def export_report_pdf(self, topology_id):
        raise NotFoundError("Topology", str(topology_id))

    async def export_report_doc(self, topology_id):
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


def test_report_endpoints_return_pdf_and_doc():
    app.dependency_overrides[get_topology_service] = lambda: FakeReportService()
    client = TestClient(app)
    topology_id = uuid.uuid4()

    try:
        pdf_response = client.get(f"/api/v1/topology/{topology_id}/report.pdf")
        doc_response = client.get(f"/api/v1/topology/{topology_id}/report.doc")
    finally:
        app.dependency_overrides.clear()

    assert pdf_response.status_code == 200
    assert pdf_response.headers["content-type"].startswith("application/pdf")
    assert pdf_response.content.startswith(b"%PDF")
    assert doc_response.status_code == 200
    assert doc_response.headers["content-type"].startswith("application/msword")
    assert doc_response.content.startswith(b"<!doctype html>")


def test_report_endpoint_returns_404_for_missing_topology():
    app.dependency_overrides[get_topology_service] = lambda: MissingReportService()
    client = TestClient(app)

    try:
        response = client.get(f"/api/v1/topology/{uuid.uuid4()}/report.md")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 404
