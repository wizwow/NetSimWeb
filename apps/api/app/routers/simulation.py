import uuid
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.events.manager import manager
from app.core.database import get_db
from app.services.simulation import SimulationService
from app.core.dependencies import get_simulation_engine

router = APIRouter(tags=["Simulation"])

@router.websocket("/ws/events/{topology_id}")
async def simulation_events_ws(websocket: WebSocket, topology_id: str):
    await manager.connect(websocket, topology_id)
    try:
        while True:
            # Attendiamo ping o comandi dal client
            data = await websocket.receive_text()
            # Al momento facciamo solo echo o ignoriamo
    except WebSocketDisconnect:
        manager.disconnect(websocket, topology_id)

@router.post("/api/v1/topology/{topology_id}/start")
async def start_simulation(
    topology_id: uuid.UUID, 
    db: AsyncSession = Depends(get_db),
    engine = Depends(get_simulation_engine)
):
    svc = SimulationService(db, engine)
    topo = await svc.start_topology(topology_id)
    
    # Notifica via WebSocket
    await manager.broadcast_to_topology(str(topology_id), {
        "type": "SIMULATION_STARTED",
        "topology_id": str(topology_id),
        "status": "running"
    })

    # Simula log di avvio per ogni nodo
    for node in topo.graph_json.get("nodes", []):
        node_id = node["id"]
        label = node.get("label", node_id)
        
        await manager.broadcast_to_topology(str(topology_id), {
            "type": "SIMULATION_LOG",
            "message": f"Powering on node {label}...",
            "level": "info",
            "source": "system"
        })
        
        await manager.broadcast_to_topology(str(topology_id), {
            "type": "NODE_STATUS_CHANGED",
            "node_id": node_id,
            "status": "booting"
        })

    return {"status": "ok", "topology_status": topo.status}

@router.post("/api/v1/topology/{topology_id}/stop")
async def stop_simulation(
    topology_id: uuid.UUID, 
    db: AsyncSession = Depends(get_db),
    engine = Depends(get_simulation_engine)
):
    svc = SimulationService(db, engine)
    topo = await svc.stop_topology(topology_id)
    
    # Notifica via WebSocket
    await manager.broadcast_to_topology(str(topology_id), {
        "type": "SIMULATION_STOPPED",
        "topology_id": str(topology_id),
        "status": "stopped"
    })
    
    return {"status": "ok", "topology_status": topo.status}
