import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.models.topology import Topology
from app.engines.base import SimulationEngineInterface
from app.events.manager import manager
from fastapi import HTTPException

class SimulationService:
    def __init__(self, db: AsyncSession, engine: SimulationEngineInterface):
        self.db = db
        self.engine = engine

    async def start_topology(self, topology_id: uuid.UUID) -> Topology:
        result = await self.db.execute(select(Topology).where(Topology.id == topology_id))
        topo = result.scalars().first()
        if not topo:
            raise HTTPException(status_code=404, detail="Topology not found")
        
        # 1. Se non ha un engine_topo_id, crealo nell'engine
        if not topo.engine_topo_id:
            engine_id = await self.engine.create_topology(topo.graph_json)
            topo.engine_topo_id = engine_id
            await self.db.commit()
            
        # 2. Avvia la simulazione
        await self.engine.start_topology(topo.engine_topo_id)
        
        # 3. Aggiorna lo stato nel DB
        topo.status = "running"
        
        # Aggiorna anche lo stato dei nodi nel graph_json per il frontend
        graph = topo.graph_json.copy()
        for node in graph.get("nodes", []):
            if "runtimeState" not in node:
                node["runtimeState"] = {}
            node["runtimeState"]["status"] = "running"
        topo.graph_json = graph
        
        await self.db.commit()
        await self.db.refresh(topo)

        tid = str(topology_id)
        await manager.broadcast_to_topology(tid, {
            "type": "SIMULATION_STARTED",
            "topology_id": tid,
            "status": "running"
        })
        for node in topo.graph_json.get("nodes", []):
            node_id = node["id"]
            label = node.get("label", node_id)
            await manager.broadcast_to_topology(tid, {
                "type": "SIMULATION_LOG",
                "message": f"Powering on node {label}...",
                "level": "info",
                "source": "system"
            })
            await manager.broadcast_to_topology(tid, {
                "type": "NODE_STATUS_CHANGED",
                "node_id": node_id,
                "status": "booting"
            })

        return topo

    async def stop_topology(self, topology_id: uuid.UUID) -> Topology:
        result = await self.db.execute(select(Topology).where(Topology.id == topology_id))
        topo = result.scalars().first()
        if not topo:
            raise HTTPException(status_code=404, detail="Topology not found")
            
        if topo.engine_topo_id:
            await self.engine.stop_topology(topo.engine_topo_id)
            
        topo.status = "stopped"
        
        # Aggiorna lo stato dei nodi nel graph_json
        graph = topo.graph_json.copy()
        for node in graph.get("nodes", []):
            if "runtimeState" not in node:
                node["runtimeState"] = {}
            node["runtimeState"]["status"] = "stopped"
        topo.graph_json = graph
        
        await self.db.commit()
        await self.db.refresh(topo)

        tid = str(topology_id)
        await manager.broadcast_to_topology(tid, {
            "type": "SIMULATION_STOPPED",
            "topology_id": tid,
            "status": "stopped"
        })

        return topo
