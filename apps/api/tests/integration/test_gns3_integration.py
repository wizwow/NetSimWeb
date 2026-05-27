"""Integration tests for GNS3 adapter against a live GNS3 server.

Run with:
    pytest -m gns3 tests/integration/test_gns3_integration.py

Requires:
    - GNS3 server running at GNS3_URL (default http://localhost:3080)
    - GNS3_USER and GNS3_PASSWORD env vars (default admin/admin)
    - GNS3_TEMPLATE_MAPPINGS env var with valid template IDs

These tests are skipped in CI by default.  Add ``-m gns3`` to run them locally.
"""

import os

import pytest

from app.core.gns3_config import load_gns3_config
from app.engines.gns3 import GNS3SimulationEngine
from app.schemas.topology import NetworkNodeSchema, TopologyBase


pytestmark = [
    pytest.mark.anyio,
    pytest.mark.gns3,
    pytest.mark.skipif(
        os.getenv("SIMULATION_ENGINE", "mock") != "gns3",
        reason="Live GNS3 tests require SIMULATION_ENGINE=gns3",
    ),
]


@pytest.fixture()
def engine():
    config = load_gns3_config()
    return GNS3SimulationEngine(
        base_url=config.base_url,
        user=config.user,
        password=config.password,
        template_mappings=config.template_mappings,
    )


async def test_create_and_start_single_node_topology(engine: GNS3SimulationEngine):
    topology = TopologyBase(
        name="Integration Test - Single Router",
        nodes=[
            NetworkNodeSchema(
                id="r1",
                label="IntegR1",
                position={"x": 0, "y": 0},
                baseType="router",
                tags=[],
            )
        ],
        edges=[],
    )

    project_id = await engine.create_topology(topology)
    assert project_id

    try:
        await engine.start_topology(project_id)
        status = await engine.get_node_status("r1")
        assert status in {"running", "booting"}
        await engine.stop_topology(project_id)
    finally:
        await engine.delete_topology(project_id)


async def test_complete_topology_lifecycle(engine: GNS3SimulationEngine):
    topology = TopologyBase(
        name="Integration Test - Multi Node Lifecycle",
        nodes=[
            NetworkNodeSchema(
                id="r1",
                label="IntegR1",
                position={"x": 0, "y": 0},
                baseType="router",
                tags=[],
            ),
            NetworkNodeSchema(
                id="r2",
                label="IntegR2",
                position={"x": 100, "y": 0},
                baseType="router",
                tags=[],
            ),
        ],
        edges=[
            {
                "id": "link-1",
                "sourceNodeId": "r1",
                "sourcePort": "eth0",
                "targetNodeId": "r2",
                "targetPort": "eth0",
                "linkType": "ethernet",
            }
        ],
    )

    project_id = await engine.create_topology(topology)
    assert project_id

    try:
        # Start topology
        await engine.start_topology(project_id)

        # Verify node statuses
        status_r1 = await engine.get_node_status("r1")
        status_r2 = await engine.get_node_status("r2")
        assert status_r1 in {"running", "booting"}
        assert status_r2 in {"running", "booting"}

        # Inject link fault (link-down)
        await engine.inject_fault("link-1", "link-down")

        # Clear fault
        await engine.clear_fault("link-1")

        # Stop topology
        await engine.stop_topology(project_id)
    finally:
        # Delete project to keep GNS3 server clean
        await engine.delete_topology(project_id)

