import uuid
from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_simulation_engine
from app.core.exceptions import NotFoundError
from app.engines.base import SimulationEngineInterface
from app.events.manager import manager
from app.schemas.topology import FaultRequestSchema, ProbeRequestSchema, ProbeResultSchema
from app.services.simulation import SimulationService

router = APIRouter(tags=["Simulation"])


def get_simulation_service(
    db: AsyncSession = Depends(get_db),
    engine: SimulationEngineInterface = Depends(get_simulation_engine),
) -> SimulationService:
    return SimulationService(db, engine)


@router.websocket("/ws/events/{topology_id}")
async def simulation_events_ws(websocket: WebSocket, topology_id: str) -> None:
    await manager.connect(websocket, topology_id)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket, topology_id)


@router.post("/api/v1/topology/{topology_id}/start")
async def start_simulation(
    topology_id: uuid.UUID,
    svc: SimulationService = Depends(get_simulation_service),
) -> dict:
    try:
        topo = await svc.start_topology(topology_id)
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=exc.detail)
    return {"status": "ok", "topology_status": topo.status}


@router.post("/api/v1/topology/{topology_id}/stop")
async def stop_simulation(
    topology_id: uuid.UUID,
    svc: SimulationService = Depends(get_simulation_service),
) -> dict:
    try:
        topo = await svc.stop_topology(topology_id)
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=exc.detail)
    return {"status": "ok", "topology_status": topo.status}


@router.post("/api/v1/topology/{topology_id}/probe", response_model=ProbeResultSchema)
async def run_probe(
    topology_id: uuid.UUID,
    probe: ProbeRequestSchema,
    svc: SimulationService = Depends(get_simulation_service),
) -> ProbeResultSchema:
    try:
        return await svc.run_probe(topology_id, probe)
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=exc.detail)


@router.post("/api/v1/topology/{topology_id}/fault")
async def inject_fault(
    topology_id: uuid.UUID,
    fault: FaultRequestSchema,
    svc: SimulationService = Depends(get_simulation_service),
) -> dict:
    try:
        topo = await svc.inject_fault(topology_id, fault)
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=exc.detail)
    return {"status": "ok", "topology_status": topo.status}
