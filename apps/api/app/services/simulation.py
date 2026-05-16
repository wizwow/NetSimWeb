import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.core.exceptions import NotFoundError
from app.models.topology import Topology
from app.schemas.topology import TopologyBase
from app.engines.base import SimulationEngineInterface
from app.events.manager import manager


class SimulationService:
    def __init__(self, db: AsyncSession, engine: SimulationEngineInterface) -> None:
        self.db = db
        self.engine = engine

    async def _get_topology(self, topology_id: uuid.UUID) -> Topology:
        result = await self.db.execute(
            select(Topology).where(Topology.id == topology_id)
        )
        topo = result.scalars().first()
        if not topo:
            raise NotFoundError("Topology", str(topology_id))
        return topo

    async def start_topology(self, topology_id: uuid.UUID) -> Topology:
        topo = await self._get_topology(topology_id)

        # 1. Provision in engine if not yet done
        if not topo.engine_topo_id:
            topo_schema = TopologyBase(
                name=topo.name,
                description=topo.description,
                abstraction_level=topo.abstraction_level,
                status=topo.status,
                nodes=topo.graph_json.get("nodes", []),
                edges=topo.graph_json.get("edges", []),
            )
            engine_id = await self.engine.create_topology(topo_schema)
            topo.engine_topo_id = engine_id
            await self.db.commit()

        # 2. Start
        await self.engine.start_topology(topo.engine_topo_id)

        # 3. Persist state
        topo.status = "running"
        graph = topo.graph_json.copy()
        for node in graph.get("nodes", []):
            if "runtimeState" not in node:
                node["runtimeState"] = {}
            node["runtimeState"]["status"] = "running"
        topo.graph_json = graph

        await self.db.commit()
        await self.db.refresh(topo)

        # 4. Broadcast typed events (SimulationEvent union)
        tid = str(topology_id)
        for node in topo.graph_json.get("nodes", []):
            await manager.broadcast_to_topology(tid, {
                "type": "NODE_STATUS_CHANGED",
                "nodeId": node["id"],
                "status": "running",
            })

        return topo

    async def stop_topology(self, topology_id: uuid.UUID) -> Topology:
        topo = await self._get_topology(topology_id)

        if topo.engine_topo_id:
            await self.engine.stop_topology(topo.engine_topo_id)

        topo.status = "stopped"
        graph = topo.graph_json.copy()
        for node in graph.get("nodes", []):
            if "runtimeState" not in node:
                node["runtimeState"] = {}
            node["runtimeState"]["status"] = "stopped"
        topo.graph_json = graph

        await self.db.commit()
        await self.db.refresh(topo)

        tid = str(topology_id)
        for node in topo.graph_json.get("nodes", []):
            await manager.broadcast_to_topology(tid, {
                "type": "NODE_STATUS_CHANGED",
                "nodeId": node["id"],
                "status": "stopped",
            })

        return topo
