from abc import ABC, abstractmethod

from app.schemas.topology import (
    FaultType,
    NodeStatus,
    ProbeResultSchema,
    ProbeType,
    TopologyBase,
)


class SimulationEngineInterface(ABC):
    """Contract for all simulation‐engine adapters (GNS3, mock, …)."""

    @abstractmethod
    async def create_topology(self, topology: TopologyBase) -> str:
        """Provision a topology in the engine.  Returns engine_topology_id."""

    @abstractmethod
    async def start_topology(self, engine_topology_id: str) -> None: ...

    @abstractmethod
    async def stop_topology(self, engine_topology_id: str) -> None: ...

    @abstractmethod
    async def get_node_status(self, engine_node_id: str) -> NodeStatus: ...

    @abstractmethod
    async def inject_fault(self, engine_link_id: str, fault: FaultType) -> None: ...

    @abstractmethod
    async def run_probe(
        self, source_node_id: str, target_ip: str, probe_type: ProbeType
    ) -> ProbeResultSchema: ...

    @abstractmethod
    async def delete_topology(self, engine_topology_id: str) -> None:
        """Delete a topology/project from the engine."""
