import asyncio
from typing import Dict, Optional

from app.engines.base import SimulationEngineInterface
from app.schemas.engine_plan import TopologyProvisioningResult
from app.schemas.topology import (
    FaultType,
    NodeStatus,
    ProbeResultSchema,
    ProbeType,
    TopologyBase,
)


class MockSimulationEngine(SimulationEngineInterface):
    """In-memory mock — responds correctly without a real GNS3 backend."""

    def __init__(self) -> None:
        self.topologies: Dict[str, TopologyBase] = {}
        self.node_statuses: Dict[str, NodeStatus] = {}

    async def create_topology(self, topology: TopologyBase) -> TopologyProvisioningResult:
        engine_id = f"mock-topo-{len(self.topologies) + 1}"
        self.topologies[engine_id] = topology
        node_id_map: Dict[str, str] = {}
        for node in topology.nodes:
            self.node_statuses[node.id] = "stopped"
            # Deterministic synthetic id keyed by the Octet node id, so
            # downstream consumers (link provisioning, status polls,
            # fault injection) can be exercised end-to-end without a
            # live GNS3 server.
            node_id_map[node.id] = f"mock-node-{node.id}"
        # Mirror the GNS3 engine: emit one synthetic link id per edge
        # in the topology. Edges are 1:1 with plan links for the mock
        # engine because the mock does not deduplicate or coalesce.
        link_id_map: Dict[str, str] = {
            edge.id: f"mock-link-{edge.id}" for edge in topology.edges
        }
        return TopologyProvisioningResult(
            engine_topology_id=engine_id,
            node_id_map=node_id_map,
            link_id_map=link_id_map,
        )

    async def start_topology(self, engine_topology_id: str) -> None:
        await asyncio.sleep(0.5)
        topo = self.topologies.get(engine_topology_id)
        if topo:
            for node in topo.nodes:
                self.node_statuses[node.id] = "running"

    async def stop_topology(self, engine_topology_id: str) -> None:
        await asyncio.sleep(0.2)
        topo = self.topologies.get(engine_topology_id)
        if topo:
            for node in topo.nodes:
                self.node_statuses[node.id] = "stopped"

    async def start_node(
        self, engine_topology_id: str, engine_node_id: str
    ) -> None:
        octet_node_id = self._octet_node_id_for(engine_topology_id, engine_node_id)
        if octet_node_id is None:
            return
        self.node_statuses[octet_node_id] = "booting"
        await asyncio.sleep(0.05)
        self.node_statuses[octet_node_id] = "running"

    async def stop_node(
        self, engine_topology_id: str, engine_node_id: str
    ) -> None:
        octet_node_id = self._octet_node_id_for(engine_topology_id, engine_node_id)
        if octet_node_id is None:
            return
        self.node_statuses[octet_node_id] = "stopped"

    async def get_node_status(
        self, engine_topology_id: str, engine_node_id: str
    ) -> NodeStatus:
        octet_node_id = self._octet_node_id_for(engine_topology_id, engine_node_id)
        if octet_node_id is None:
            return "error"
        return self.node_statuses.get(octet_node_id, "error")

    def _octet_node_id_for(
        self, engine_topology_id: str, engine_node_id: str
    ) -> Optional[str]:
        """Reverse-lookup the Octet node id for a synthetic mock engine id.

        Returns ``None`` if the engine_topology_id is unknown or the
        engine_node_id does not belong to it. This mirrors the
        defensive behaviour of the GNS3 adapter (which 404s on unknown
        nodes) without needing the mock to raise.
        """
        topo = self.topologies.get(engine_topology_id)
        if topo is None:
            return None
        for node in topo.nodes:
            if f"mock-node-{node.id}" == engine_node_id:
                return node.id
        return None

    async def inject_fault(self, engine_link_id: str, fault: FaultType) -> None:
        pass  # Mock: V2 will publish a Redis event

    async def run_probe(
        self, source_node_id: str, target_ip: str, probe_type: ProbeType
    ) -> ProbeResultSchema:
        await asyncio.sleep(0.3)
        return ProbeResultSchema(
            success=True, output=f"Reply from {target_ip}: 3ms", rttMs=3.0
        )
