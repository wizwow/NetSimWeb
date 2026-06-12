import logging
import uuid
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.core.exceptions import NotFoundError
from app.models.topology import Topology
from app.schemas.topology import FaultRequestSchema, ProbeRequestSchema, ProbeResultSchema, TopologyBase
from app.engines.base import SimulationEngineInterface
from app.events.manager import manager


logger = logging.getLogger(__name__)


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
            result = await self.engine.create_topology(topo_schema)
            topo.engine_topo_id = result.engine_topology_id
            # Persist Octet \u2194 engine id mappings so subsequent operations
            # (link provisioning, status polls, fault injection) can find
            # the engine-side objects without re-provisioning.
            topo.gns3_mappings = {
                "nodes": dict(result.node_id_map),
                "links": dict(result.link_id_map),
            }
            await self.db.commit()

        # 2. Open the project.
        await self.engine.start_topology(topo.engine_topo_id)

        # 3. Start each node individually (Phase 4). A node-start
        #    failure on one node must not block the others — a partial
        #    start is surfaced via the per-node status query in step 4
        #    rather than a 5xx for the whole request.
        node_id_map = self._node_id_map(topo)
        for engine_node_id in node_id_map.values():
            try:
                await self.engine.start_node(topo.engine_topo_id, engine_node_id)
            except Exception as exc:  # noqa: BLE001 — per-node errors must not abort the loop
                logger.warning(
                    "Failed to start engine node %s in project %s: %s",
                    engine_node_id,
                    topo.engine_topo_id,
                    exc,
                )

        # 4. Query each node's actual status and persist it. Nodes that
        #    the engine does not know about (e.g. removed externally) get
        #    status "error" so the UI can surface a precise message
        #    instead of a stale "running".
        topo.status = "running"
        graph = topo.graph_json.copy()
        for node in graph.get("nodes", []):
            if "runtimeState" not in node:
                node["runtimeState"] = {}
            engine_node_id = node_id_map.get(node["id"])
            if engine_node_id is None:
                node["runtimeState"]["status"] = "error"
            else:
                try:
                    node["runtimeState"]["status"] = await self.engine.get_node_status(
                        topo.engine_topo_id, engine_node_id
                    )
                except Exception as exc:  # noqa: BLE001
                    logger.warning(
                        "Failed to query status of engine node %s: %s",
                        engine_node_id,
                        exc,
                    )
                    node["runtimeState"]["status"] = "error"
        topo.graph_json = graph

        await self.db.commit()
        await self.db.refresh(topo)

        # 5. Broadcast typed events (SimulationEvent union) with the
        #    real per-node status from the engine.
        tid = str(topology_id)
        for node in topo.graph_json.get("nodes", []):
            actual_status = node.get("runtimeState", {}).get("status", "running")
            await manager.broadcast_to_topology(tid, {
                "type": "NODE_STATUS_CHANGED",
                "nodeId": node["id"],
                "status": actual_status,
            })

        return topo

    async def stop_topology(self, topology_id: uuid.UUID) -> Topology:
        topo = await self._get_topology(topology_id)

        # 1. Stop each node individually (Phase 4). Same best-effort
        #    semantics as the per-node start: one node failing to stop
        #    does not block the others.
        node_id_map = self._node_id_map(topo)
        for engine_node_id in node_id_map.values():
            try:
                await self.engine.stop_node(topo.engine_topo_id, engine_node_id)
            except Exception as exc:  # noqa: BLE001
                logger.warning(
                    "Failed to stop engine node %s in project %s: %s",
                    engine_node_id,
                    topo.engine_topo_id,
                    exc,
                )

        # 2. Close the project.
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

    @staticmethod
    def _node_id_map(topo: Topology) -> dict[str, str]:
        """Return the persisted Octet \u2194 engine node id mapping.

        Defensive against ``gns3_mappings`` being ``None`` (legacy
        topologies provisioned before Phase 2) or a non-dict value. An
        empty dict means the service cannot perform per-node start /
        stop / status and the call path degenerates to project-level
        operations only.
        """
        if not topo.gns3_mappings:
            return {}
        nodes = topo.gns3_mappings.get("nodes") if isinstance(topo.gns3_mappings, dict) else None
        return dict(nodes or {})

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
