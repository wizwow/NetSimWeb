from abc import ABC, abstractmethod

from app.schemas.engine_plan import TopologyProvisioningResult
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
    async def create_topology(self, topology: TopologyBase) -> TopologyProvisioningResult:
        """Provision a topology in the engine.

        Returns a :class:`TopologyProvisioningResult` containing the engine
        topology id (e.g. GNS3 project id) and any id mappings the engine
        was able to populate at provision time. Implementations must
        populate ``node_id_map`` for every node in the translated plan
        (the mock engine uses deterministic synthetic ids, the GNS3
        engine uses the ``node_id`` returned by ``POST /v2/projects/{id}/nodes``).
        ``link_id_map`` may be empty for engines that have not yet
        implemented link provisioning.
        """

    @abstractmethod
    async def start_topology(self, engine_topology_id: str) -> None: ...

    @abstractmethod
    async def stop_topology(self, engine_topology_id: str) -> None: ...

    @abstractmethod
    async def start_node(
        self, engine_topology_id: str, engine_node_id: str
    ) -> None:
        """Start a single node inside an already-opened project.

        The simulation service calls this in a loop after
        :py:meth:`start_topology` so the engine-side lifecycle of each
        node is exercised independently. Engines that do not expose a
        per-node lifecycle (e.g. legacy emulators) may implement this
        as a no-op; the simulation service still records the node as
        ``"running"`` so the UI stays consistent.
        """

    @abstractmethod
    async def stop_node(
        self, engine_topology_id: str, engine_node_id: str
    ) -> None:
        """Stop a single node inside an already-opened project.

        Symmetric counterpart to :py:meth:`start_node`. Called by the
        simulation service before :py:meth:`stop_topology` so per-node
        state is reconciled before the project is closed.
        """

    @abstractmethod
    async def get_node_status(
        self, engine_topology_id: str, engine_node_id: str
    ) -> NodeStatus: ...


    @abstractmethod
    async def inject_fault(self, engine_link_id: str, fault: FaultType) -> None: ...

    @abstractmethod
    async def run_probe(
        self, source_node_id: str, target_ip: str, probe_type: ProbeType
    ) -> ProbeResultSchema: ...
