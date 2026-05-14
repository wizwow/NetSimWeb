from abc import ABC, abstractmethod
from typing import Any, Dict

class SimulationEngineInterface(ABC):
    @abstractmethod
    async def create_topology(self, topology: Dict[str, Any]) -> str:
        """Restituisce engine_topology_id"""
        pass

    @abstractmethod
    async def start_topology(self, engine_topology_id: str) -> None:
        pass

    @abstractmethod
    async def stop_topology(self, engine_topology_id: str) -> None:
        pass

    @abstractmethod
    async def get_node_status(self, engine_node_id: str) -> str:
        pass

    @abstractmethod
    async def inject_fault(self, engine_link_id: str, fault: Dict[str, Any]) -> None:
        pass

    @abstractmethod
    async def run_probe(self, source_node_id: str, target_ip: str, probe_type: str) -> Dict[str, Any]:
        pass
