import uuid
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.core.exceptions import NotFoundError
from app.models.topology import Topology
from app.schemas.topology import FaultRequestSchema, ProbeRequestSchema, ProbeResultSchema, TopologyBase
from app.engines.base import SimulationEngineInterface
from app.events.manager import manager


class SimulationService:
    def __init__(
        self,
        db: AsyncSession,
        engine: SimulationEngineInterface,
        owner_id: uuid.UUID | None = None,
    ) -> None:
        self.db = db
        self.engine = engine
        self.owner_id = owner_id

    async def _get_topology(self, topology_id: uuid.UUID) -> Topology:
        query = select(Topology).where(Topology.id == topology_id)
        if self.owner_id is not None:
            query = query.where(Topology.owner_id == self.owner_id)
        result = await self.db.execute(
            query
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

            # Persist GNS3 registries so they survive API restarts
            if hasattr(self.engine, "export_registries"):
                graph = topo.graph_json.copy()
                graph["engine_metadata"] = self.engine.export_registries()
                topo.graph_json = graph

            await self.db.commit()
        else:
            # Reload registries from persisted metadata
            if hasattr(self.engine, "load_registries"):
                self.engine.load_registries(
                    topo.graph_json.get("engine_metadata")
                )

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

    async def run_probe(
        self,
        topology_id: uuid.UUID,
        probe: ProbeRequestSchema,
    ) -> ProbeResultSchema:
        await self._get_topology(topology_id)
        result = await self.engine.run_probe(
            source_node_id=probe.sourceNodeId,
            target_ip=probe.targetIp,
            probe_type=probe.probeType,
        )

        await manager.broadcast_to_topology(str(topology_id), {
            "type": "PROBE_RESULT",
            "probeId": f"probe-{probe.sourceNodeId}-{probe.targetIp}",
            "result": result.model_dump(),
        })
        return result

    async def inject_fault(
        self,
        topology_id: uuid.UUID,
        fault: FaultRequestSchema,
    ) -> Topology:
        topo = await self._get_topology(topology_id)
        await self.engine.inject_fault(fault.linkId, fault.faultType)

        graph = topo.graph_json.copy()
        for edge in graph.get("edges", []):
            if edge.get("id") == fault.linkId:
                edge["faultState"] = {
                    "active": True,
                    "type": fault.faultType,
                    "triggeredAt": datetime.now(timezone.utc).isoformat(),
                }
                break

        topo.graph_json = graph
        await self.db.commit()
        await self.db.refresh(topo)

        await manager.broadcast_to_topology(str(topology_id), {
            "type": "LINK_FAULT_INJECTED",
            "linkId": fault.linkId,
            "faultType": fault.faultType,
        })
        return topo
