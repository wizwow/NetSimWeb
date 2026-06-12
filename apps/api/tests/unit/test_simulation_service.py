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
        self.start_node_calls: list[tuple[str, str]] = []
        self.stop_node_calls: list[tuple[str, str]] = []
        self.status_calls: list[tuple[str, str]] = []

    async def create_topology(self, topology):
        self.create_called_with = topology
        return self._result

    async def start_topology(self, engine_topology_id):
        self.start_called_with = engine_topology_id

    async def stop_topology(self, engine_topology_id):
        self.stop_called_with = engine_topology_id

    async def start_node(self, engine_topology_id, engine_node_id):
        self.start_node_calls.append((engine_topology_id, engine_node_id))

    async def stop_node(self, engine_topology_id, engine_node_id):
        self.stop_node_calls.append((engine_topology_id, engine_node_id))

    async def get_node_status(self, engine_topology_id, engine_node_id):
        # Simulate a freshly-started node reporting "running" so the
        # service can persist a realistic per-node status.
        self.status_calls.append((engine_topology_id, engine_node_id))
        return "running"

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
            link_id_map={"link-1": "gns3-link-1"},
        )
    )
    svc = SimulationService(db, engine)

    result = await svc.start_topology(db_topo.id)

    assert result.engine_topo_id == "gns3-project-1"
    assert result.gns3_mappings == {
        "nodes": {"r1": "gns3-node-1", "r2": "gns3-node-2"},
        "links": {"link-1": "gns3-link-1"},
    }
    assert engine.start_called_with == "gns3-project-1"
    assert result.status == "running"
    # Two commits: one after provisioning, one after marking running.
    assert db.commits >= 2
    # Phase 4: after the project is opened, each node must be started
    # individually via engine.start_node(project_id, engine_node_id)
    # and queried for its real status via engine.get_node_status.
    assert engine.start_node_calls == [
        ("gns3-project-1", "gns3-node-1"),
        ("gns3-project-1", "gns3-node-2"),
    ]
    assert {node_id for _, node_id in engine.status_calls} == {
        "gns3-node-1",
        "gns3-node-2",
    }


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


async def test_stop_topology_stops_each_node_before_closing_project():
    """Phase 4: stop_topology must iterate the persisted node_id_map
    and call engine.stop_node for each node, then close the project.
    A node that the engine does not know about is simply skipped (the
    defensive empty-mapping branch in the service).
    """
    db_topo = _make_topology(
        engine_topo_id="gns3-project-1",
        gns3_mappings={
            "nodes": {"r1": "gns3-node-1", "r2": "gns3-node-2"},
            "links": {},
        },
    )
    db = _FakeAsyncSession(db_topo)
    engine = _FakeEngine(
        TopologyProvisioningResult(
            engine_topology_id="gns3-project-1",
            node_id_map={},
            link_id_map={},
        )
    )
    svc = SimulationService(db, engine)

    result = await svc.stop_topology(db_topo.id)

    assert result.status == "stopped"
    assert engine.stop_node_calls == [
        ("gns3-project-1", "gns3-node-1"),
        ("gns3-project-1", "gns3-node-2"),
    ]
    # Per-node stops must complete before the project is closed.
    assert engine.stop_called_with == "gns3-project-1"


async def test_stop_topology_is_safe_when_gns3_mappings_is_missing():
    """A topology provisioned before Phase 2 (no gns3_mappings column)
    must not crash the stop path. The service falls back to
    project-level stop only, with no per-node calls.
    """
    db_topo = _make_topology(
        engine_topo_id="legacy-project",
        gns3_mappings=None,
    )
    db = _FakeAsyncSession(db_topo)
    engine = _FakeEngine(
        TopologyProvisioningResult(engine_topology_id="x", node_id_map={})
    )
    svc = SimulationService(db, engine)

    result = await svc.stop_topology(db_topo.id)

    assert result.status == "stopped"
    assert engine.stop_node_calls == []
    assert engine.stop_called_with == "legacy-project"


async def test_start_topology_marks_node_as_error_when_missing_from_mapping():
    """A node that exists in ``graph_json.nodes`` but not in the persisted
    ``gns3_mappings.nodes`` (e.g. added to the canvas after the project
    was provisioned) must be marked ``"error"`` in runtimeState rather
    than reported as ``"running"`` — there is no engine-side object for
    the service to query, so pretending it is healthy would be a lie.
    """
    db_topo = _make_topology(
        engine_topo_id="gns3-project-1",
        gns3_mappings={"nodes": {"r1": "gns3-node-1"}, "links": {}},
    )
    # r2 lives in graph_json but was never provisioned in the engine.
    db_topo.graph_json = {
        "nodes": [
            {"id": "r1", "label": "R1"},
            {"id": "r2", "label": "R2"},  # not in gns3_mappings.nodes
        ],
        "edges": [],
    }
    db = _FakeAsyncSession(db_topo)
    engine = _FakeEngine(
        TopologyProvisioningResult(
            engine_topology_id="gns3-project-1",
            node_id_map={"r1": "gns3-node-1"},
            link_id_map={},
        )
    )
    svc = SimulationService(db, engine)

    await svc.start_topology(db_topo.id)

    statuses_by_id = {
        n["id"]: n["runtimeState"]["status"]
        for n in db_topo.graph_json["nodes"]
    }
    assert statuses_by_id["r1"] == "running"
    assert statuses_by_id["r2"] == "error"
