"""GNS3 simulation engine adapter — stub for future implementation.

All GNS3 HTTP interactions are encapsulated here.
No other module may call GNS3 directly (ARCHITECTURE.md §3.2).
"""

from app.engines.base import SimulationEngineInterface
from app.schemas.topology import (
    FaultType,
    NodeStatus,
    ProbeResultSchema,
    ProbeType,
    TopologyBase,
)


class GNS3SimulationEngine(SimulationEngineInterface):
    """Adapter for a self-hosted GNS3 Server.  Not yet implemented."""

    def __init__(self, base_url: str, user: str, password: str) -> None:
        self.base_url = base_url
        self.user = user
        self.password = password

    async def create_topology(self, topology: TopologyBase) -> str:
        raise NotImplementedError("GNS3 engine not yet implemented")

    async def start_topology(self, engine_topology_id: str) -> None:
        raise NotImplementedError("GNS3 engine not yet implemented")

    async def stop_topology(self, engine_topology_id: str) -> None:
        raise NotImplementedError("GNS3 engine not yet implemented")

    async def get_node_status(self, engine_node_id: str) -> NodeStatus:
        raise NotImplementedError("GNS3 engine not yet implemented")

    async def inject_fault(self, engine_link_id: str, fault: FaultType) -> None:
        raise NotImplementedError("GNS3 engine not yet implemented")

    async def run_probe(
        self, source_node_id: str, target_ip: str, probe_type: ProbeType
    ) -> ProbeResultSchema:
        raise NotImplementedError("GNS3 engine not yet implemented")
