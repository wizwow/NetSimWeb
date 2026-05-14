import asyncio
from typing import Any, Dict
from app.engines.base import SimulationEngineInterface

class MockSimulationEngine(SimulationEngineInterface):
    def __init__(self):
        self.topologies = {}
        self.node_statuses = {}

    async def create_topology(self, topology: Dict[str, Any]) -> str:
        engine_id = f"mock-topo-{len(self.topologies) + 1}"
        self.topologies[engine_id] = topology
        
        # Inizializza tutti i nodi come stopped
        for node in topology.get("nodes", []):
            self.node_statuses[node["id"]] = "stopped"
            
        return engine_id

    async def start_topology(self, engine_topology_id: str) -> None:
        await asyncio.sleep(0.5) # Simula delay avvio
        if engine_topology_id in self.topologies:
            for node in self.topologies[engine_topology_id].get("nodes", []):
                self.node_statuses[node["id"]] = "running"

    async def stop_topology(self, engine_topology_id: str) -> None:
        await asyncio.sleep(0.2)
        if engine_topology_id in self.topologies:
            for node in self.topologies[engine_topology_id].get("nodes", []):
                self.node_statuses[node["id"]] = "stopped"

    async def get_node_status(self, engine_node_id: str) -> str:
        return self.node_statuses.get(engine_node_id, "error")

    async def inject_fault(self, engine_link_id: str, fault: Dict[str, Any]) -> None:
        pass # Mock: in una V2 invierà evento pub/sub

    async def run_probe(self, source_node_id: str, target_ip: str, probe_type: str) -> Dict[str, Any]:
        await asyncio.sleep(0.3)
        return {"success": True, "output": f"Reply from {target_ip}: 3ms", "rttMs": 3}
