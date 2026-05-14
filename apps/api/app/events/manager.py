from typing import List, Dict
from fastapi import WebSocket

class ConnectionManager:
    def __init__(self):
        # Mappa topology_id -> lista di websocket attivi
        self.active_connections: Dict[str, List[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, topology_id: str):
        await websocket.accept()
        if topology_id not in self.active_connections:
            self.active_connections[topology_id] = []
        self.active_connections[topology_id].append(websocket)

    def disconnect(self, websocket: WebSocket, topology_id: str):
        if topology_id in self.active_connections:
            try:
                self.active_connections[topology_id].remove(websocket)
                if not self.active_connections[topology_id]:
                    del self.active_connections[topology_id]
            except ValueError:
                pass

    async def broadcast_to_topology(self, topology_id: str, message: dict):
        if topology_id in self.active_connections:
            for connection in self.active_connections[topology_id]:
                try:
                    await connection.send_json(message)
                except Exception:
                    # Rimuovi connessioni morte se necessario
                    pass

manager = ConnectionManager()
