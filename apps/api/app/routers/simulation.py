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
            await websocket.receive_text()
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
    return {"status": "ok", "topology_status": topo.status}

@router.post("/api/v1/topology/{topology_id}/stop")
async def stop_simulation(
    topology_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    engine = Depends(get_simulation_engine)
):
    svc = SimulationService(db, engine)
    topo = await svc.stop_topology(topology_id)
    return {"status": "ok", "topology_status": topo.status}
