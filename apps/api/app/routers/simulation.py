from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from typing import Dict
import uuid

router = APIRouter(prefix="/ws", tags=["Simulation Events"])

class ConnectionManager:
    def __init__(self):
        # topology_id -> list of websockets
        self.active_connections: Dict[str, list[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, topology_id: str):
        await websocket.accept()
        if topology_id not in self.active_connections:
            self.active_connections[topology_id] = []
        self.active_connections[topology_id].append(websocket)

    def disconnect(self, websocket: WebSocket, topology_id: str):
        if topology_id in self.active_connections:
            self.active_connections[topology_id].remove(websocket)

    async def broadcast(self, message: str, topology_id: str):
        if topology_id in self.active_connections:
            for connection in self.active_connections[topology_id]:
                await connection.send_text(message)

manager = ConnectionManager()

@router.websocket("/events/{topology_id}")
async def simulation_events_ws(websocket: WebSocket, topology_id: str):
    await manager.connect(websocket, topology_id)
    try:
        while True:
            # Attendiamo ping o comandi dal client
            data = await websocket.receive_text()
            # Al momento facciamo solo echo
            await manager.broadcast(f"Echo from server: {data}", topology_id)
    except WebSocketDisconnect:
        manager.disconnect(websocket, topology_id)
