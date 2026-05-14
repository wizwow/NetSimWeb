import uuid
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.models.topology import Topology
from app.engines.base import SimulationEngineInterface
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
        
        # TODO: Inviare evento WebSocket (publisher)
        
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
        
        # TODO: Inviare evento WebSocket (publisher)
        
        return topo
