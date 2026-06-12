"""Unit tests for :class:`SimulationService`.

These tests exercise the service contract directly with a fake engine and
fake AsyncSession — no DB, no HTTP, no Docker. They focus on the
``start_topology`` path that persists engine id mappings (Phase 2 of the
GNS3 integration plan).
"""

import uuid
from types import SimpleNamespace

import pytest

from app.engines.base import SimulationEngineInterface
from app.schemas.engine_plan import TopologyProvisioningResult
from app.schemas.topology import ProbeResultSchema
from app.services.simulation import SimulationService


pytestmark = pytest.mark.anyio


class _FakeScalarResult:
    def __init__(self, item):
        self._item = item

    def scalars(self):
        return self

    def first(self):
        return self._item


class _FakeAsyncSession:
    """In-memory AsyncSession stub that returns a fixed topology and counts commits."""

    def __init__(self, topology):
        self._topology = topology
        self.commits = 0
        self.refreshes = 0

    async def execute(self, query):
        return _FakeScalarResult(self._topology)

    async def commit(self):
        self.commits += 1

    async def refresh(self, instance):
        self.refreshes += 1
        return instance


class _FakeEngine(SimulationEngineInterface):
    """In-memory engine stub that records calls and returns a fixed result."""

    def __init__(self, result: TopologyProvisioningResult) -> None:
        self._result = result
        self.create_called_with = None
        self.start_called_with = None
        self.stop_called_with = None

    async def create_topology(self, topology):
        self.create_called_with = topology
        return self._result

    async def start_topology(self, engine_topology_id):
        self.start_called_with = engine_topology_id

    async def stop_topology(self, engine_topology_id):
        self.stop_called_with = engine_topology_id

    async def get_node_status(self, engine_node_id):
        return "stopped"

    async def inject_fault(self, engine_link_id, fault):
        pass

    async def run_probe(self, source_node_id, target_ip, probe_type):
        return ProbeResultSchema(success=True, output="", rttMs=0)


def _make_topology(engine_topo_id=None, gns3_mappings=None):
    """Build a SimpleNamespace that quacks like a Topology ORM row."""
    return SimpleNamespace(
        id=uuid.uuid4(),
        name="Test",
        description=None,
        abstraction_level="logical",
        status="draft",
        engine_topo_id=engine_topo_id,
        gns3_mappings=gns3_mappings,
        graph_json={"nodes": [], "edges": []},
    )


async def test_start_topology_persists_gns3_mappings_from_engine_result():
    """When the engine returns a node_id_map, the service writes it onto
    ``topo.gns3_mappings`` so subsequent operations (link provisioning,
    status polls, fault injection) can find the engine-side objects.
    """
    db_topo = _make_topology()
    db = _FakeAsyncSession(db_topo)
    engine = _FakeEngine(
        TopologyProvisioningResult(
            engine_topology_id="gns3-project-1",
            node_id_map={"r1": "gns3-node-1", "r2": "gns3-node-2"},
        )
    )
    svc = SimulationService(db, engine)

    result = await svc.start_topology(db_topo.id)

    assert result.engine_topo_id == "gns3-project-1"
    assert result.gns3_mappings == {
        "nodes": {"r1": "gns3-node-1", "r2": "gns3-node-2"},
        "links": {},
    }
    assert engine.start_called_with == "gns3-project-1"
    assert result.status == "running"
    # Two commits: one after provisioning, one after marking running.
    assert db.commits >= 2


async def test_start_topology_reuses_existing_engine_topo_id_without_reprovisioning():
    """A topology that has already been provisioned must not call
    create_topology again — only start_topology. This is the
    idempotency contract that makes "Start" a safe re-entrant operation.
    """
    db_topo = _make_topology(
        engine_topo_id="existing-project",
        gns3_mappings={"nodes": {"r1": "old"}, "links": {}},
    )
    db = _FakeAsyncSession(db_topo)
    engine = _FakeEngine(
        TopologyProvisioningResult(engine_topology_id="new", node_id_map={})
    )
    svc = SimulationService(db, engine)

    await svc.start_topology(db_topo.id)

    assert engine.create_called_with is None
    assert engine.start_called_with == "existing-project"
    # gns3_mappings was not overwritten by a re-provisioning pass.
    assert db_topo.gns3_mappings == {"nodes": {"r1": "old"}, "links": {}}
