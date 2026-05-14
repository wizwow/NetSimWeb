import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import delete, update
from typing import List

from app.core.database import get_db
from app.models.topology import Topology
from app.schemas.topology import TopologyCreate, TopologyRead, TopologyUpdate, TopologyBase
from app.services.autoip import assign_topology_ips

router = APIRouter(prefix="/topology", tags=["Topologies"])

@router.post("/autoip", response_model=TopologyBase)
async def auto_assign_ips(topo_in: TopologyBase):
    nodes, edges = assign_topology_ips(topo_in.nodes, topo_in.edges)
    topo_in.nodes = nodes
    topo_in.edges = edges
    return topo_in

@router.post("/", response_model=TopologyRead, status_code=status.HTTP_201_CREATED)
async def create_topology(topo_in: TopologyCreate, db: AsyncSession = Depends(get_db)):
    graph_json = {
        "nodes": [n.model_dump() for n in topo_in.nodes],
        "edges": [e.model_dump() for e in topo_in.edges]
    }
    db_topo = Topology(
        name=topo_in.name,
        description=topo_in.description,
        abstraction_level=topo_in.abstraction_level,
        status=topo_in.status,
        graph_json=graph_json
    )
    db.add(db_topo)
    await db.commit()
    await db.refresh(db_topo)
    
    # Costruisci risposta
    response_data = db_topo.__dict__.copy()
    response_data["nodes"] = db_topo.graph_json.get("nodes", [])
    response_data["edges"] = db_topo.graph_json.get("edges", [])
    return response_data

@router.get("/", response_model=List[TopologyRead])
async def list_topologies(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Topology))
    topologies = result.scalars().all()
    
    responses = []
    for t in topologies:
        data = t.__dict__.copy()
        data["nodes"] = t.graph_json.get("nodes", [])
        data["edges"] = t.graph_json.get("edges", [])
        responses.append(data)
    return responses

@router.get("/{topology_id}", response_model=TopologyRead)
async def get_topology(topology_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Topology).where(Topology.id == topology_id))
    topo = result.scalars().first()
    if not topo:
        raise HTTPException(status_code=404, detail="Topology not found")
        
    data = topo.__dict__.copy()
    data["nodes"] = topo.graph_json.get("nodes", [])
    data["edges"] = topo.graph_json.get("edges", [])
    return data

@router.put("/{topology_id}", response_model=TopologyRead)
async def update_topology(topology_id: uuid.UUID, topo_in: TopologyUpdate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Topology).where(Topology.id == topology_id))
    db_topo = result.scalars().first()
    if not db_topo:
        raise HTTPException(status_code=404, detail="Topology not found")
        
    update_data = topo_in.model_dump(exclude_unset=True)
    
    # Gestione speciale per nodes/edges
    if "nodes" in update_data or "edges" in update_data:
        graph_json = db_topo.graph_json.copy()
        if "nodes" in update_data:
            graph_json["nodes"] = update_data["nodes"]
            del update_data["nodes"]
        if "edges" in update_data:
            graph_json["edges"] = update_data["edges"]
            del update_data["edges"]
        db_topo.graph_json = graph_json
        
    for key, value in update_data.items():
        setattr(db_topo, key, value)
        
    await db.commit()
    await db.refresh(db_topo)
    
    data = db_topo.__dict__.copy()
    data["nodes"] = db_topo.graph_json.get("nodes", [])
    data["edges"] = db_topo.graph_json.get("edges", [])
    return data

@router.delete("/{topology_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_topology(topology_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Topology).where(Topology.id == topology_id))
    topo = result.scalars().first()
    if not topo:
        raise HTTPException(status_code=404, detail="Topology not found")
    await db.delete(topo)
    await db.commit()
    return None
