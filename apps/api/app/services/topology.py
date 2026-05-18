import uuid
from datetime import datetime, timezone
from typing import List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import desc

from app.core.exceptions import NotFoundError
from app.models.topology import Topology
from app.schemas.topology import (
    TopologyBase,
    TopologyCreate,
    TopologyExportSchema,
    TopologyImportSchema,
    TopologyUpdate,
)
from app.services.autoip import assign_topology_ips
from app.services.report import generate_doc_report, generate_markdown_report, generate_pdf_report


class TopologyService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    def auto_assign_ips(self, topo: TopologyBase) -> TopologyBase:
        nodes, edges = assign_topology_ips(topo.nodes, topo.edges)
        topo.nodes = nodes
        topo.edges = edges
        return topo

    async def create(self, topo_in: TopologyCreate) -> Topology:
        graph_json = {
            "nodes": [n.model_dump() for n in topo_in.nodes],
            "edges": [e.model_dump() for e in topo_in.edges],
        }
        db_topo = Topology(
            name=topo_in.name,
            description=topo_in.description,
            abstraction_level=topo_in.abstraction_level,
            status=topo_in.status,
            graph_json=graph_json,
        )
        self.db.add(db_topo)
        await self.db.commit()
        await self.db.refresh(db_topo)
        return db_topo

    async def list_all(self) -> List[Topology]:
        result = await self.db.execute(
            select(Topology).order_by(desc(Topology.created_at))
        )
        return result.scalars().all()

    async def get(self, topology_id: uuid.UUID) -> Topology:
        result = await self.db.execute(
            select(Topology).where(Topology.id == topology_id)
        )
        topo = result.scalars().first()
        if not topo:
            raise NotFoundError("Topology", str(topology_id))
        return topo

    async def update(self, topology_id: uuid.UUID, topo_in: TopologyUpdate) -> Topology:
        db_topo = await self.get(topology_id)
        update_data = topo_in.model_dump(exclude_unset=True)

        if "nodes" in update_data or "edges" in update_data:
            graph_json = db_topo.graph_json.copy()
            if "nodes" in update_data:
                graph_json["nodes"] = update_data.pop("nodes")
            if "edges" in update_data:
                graph_json["edges"] = update_data.pop("edges")
            db_topo.graph_json = graph_json

        for key, value in update_data.items():
            setattr(db_topo, key, value)

        await self.db.commit()
        await self.db.refresh(db_topo)
        return db_topo

    async def delete(self, topology_id: uuid.UUID) -> None:
        db_topo = await self.get(topology_id)
        await self.db.delete(db_topo)
        await self.db.commit()

    async def export_topology(self, topology_id: uuid.UUID) -> TopologyExportSchema:
        topo = await self.get(topology_id)
        graph = topo.graph_json or {}
        return TopologyExportSchema(
            topologyId=topo.id,
            name=topo.name,
            description=topo.description,
            abstractionLevel=topo.abstraction_level,
            status=topo.status,
            engineTopoId=topo.engine_topo_id,
            exportedAt=datetime.now(timezone.utc).isoformat(),
            nodes=graph.get("nodes", []),
            edges=graph.get("edges", []),
        )

    async def import_topology(self, import_data: TopologyImportSchema) -> Topology:
        graph_json = {
            "nodes": [n.model_dump() for n in import_data.nodes],
            "edges": [e.model_dump() for e in import_data.edges],
        }
        db_topo = Topology(
            name=import_data.name,
            description=import_data.description,
            abstraction_level=import_data.abstractionLevel,
            status="draft",
            graph_json=graph_json,
        )
        self.db.add(db_topo)
        await self.db.commit()
        await self.db.refresh(db_topo)
        return db_topo

    async def export_report_markdown(self, topology_id: uuid.UUID) -> str:
        topo = await self.get(topology_id)
        return generate_markdown_report(topo)

    async def export_report_pdf(self, topology_id: uuid.UUID) -> bytes:
        topo = await self.get(topology_id)
        return generate_pdf_report(topo)

    async def export_report_doc(self, topology_id: uuid.UUID) -> bytes:
        topo = await self.get(topology_id)
        return generate_doc_report(topo)

    @staticmethod
    def to_response(topo: Topology) -> dict:
        data = {
            "id": topo.id,
            "name": topo.name,
            "description": topo.description,
            "abstraction_level": topo.abstraction_level,
            "status": topo.status,
            "owner_id": topo.owner_id,
            "engine_topo_id": topo.engine_topo_id,
            "created_at": topo.created_at,
            "updated_at": topo.updated_at,
            "nodes": topo.graph_json.get("nodes", []),
            "edges": topo.graph_json.get("edges", []),
        }
        return data
