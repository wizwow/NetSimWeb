import asyncio
import json
import os
import uuid
from contextlib import suppress
from typing import Dict, List

from fastapi import WebSocket
from redis.asyncio import Redis


class ConnectionManager:
    def __init__(self):
        # Mappa topology_id -> lista di websocket attivi
        self.active_connections: Dict[str, List[WebSocket]] = {}
        self._redis: Redis | None = None
        self._subscription_tasks: Dict[str, asyncio.Task] = {}
        self._instance_id = str(uuid.uuid4())

    async def connect(self, websocket: WebSocket, topology_id: str):
        await websocket.accept()
        if topology_id not in self.active_connections:
            self.active_connections[topology_id] = []
        self.active_connections[topology_id].append(websocket)
        await self._ensure_subscription(topology_id)

    def disconnect(self, websocket: WebSocket, topology_id: str):
        if topology_id in self.active_connections:
            try:
                self.active_connections[topology_id].remove(websocket)
                if not self.active_connections[topology_id]:
                    del self.active_connections[topology_id]
                    self._stop_subscription(topology_id)
            except ValueError:
                pass

    async def broadcast_to_topology(self, topology_id: str, message: dict):
        await self._publish_to_redis(topology_id, message)
        await self._send_local(topology_id, message)

    async def _send_local(self, topology_id: str, message: dict) -> None:
        dead_connections: List[WebSocket] = []
        for connection in self.active_connections.get(topology_id, []):
            try:
                await connection.send_json(message)
            except Exception:
                dead_connections.append(connection)

        for connection in dead_connections:
            self.disconnect(connection, topology_id)

    async def _publish_to_redis(self, topology_id: str, message: dict) -> None:
        redis = await self._get_redis()
        if redis is None:
            return

        payload = {
            "origin": self._instance_id,
            "message": message,
        }
        try:
            await redis.publish(self._channel(topology_id), json.dumps(payload))
        except Exception:
            await self._close_redis()

    async def _ensure_subscription(self, topology_id: str) -> None:
        if topology_id in self._subscription_tasks:
            return

        redis = await self._get_redis()
        if redis is None:
            return

        self._subscription_tasks[topology_id] = asyncio.create_task(
            self._listen_to_redis(topology_id, redis),
        )

    def _stop_subscription(self, topology_id: str) -> None:
        task = self._subscription_tasks.pop(topology_id, None)
        if task:
            task.cancel()

    async def _listen_to_redis(self, topology_id: str, redis: Redis) -> None:
        pubsub = redis.pubsub()
        try:
            await pubsub.subscribe(self._channel(topology_id))
            async for item in pubsub.listen():
                if item.get("type") != "message":
                    continue

                payload = json.loads(item["data"])
                if payload.get("origin") == self._instance_id:
                    continue

                message = payload.get("message", payload)
                await self._send_local(topology_id, message)
        except asyncio.CancelledError:
            raise
        except Exception:
            await self._close_redis()
        finally:
            with suppress(Exception):
                await pubsub.unsubscribe(self._channel(topology_id))
                await pubsub.close()

    async def _get_redis(self) -> Redis | None:
        if self._redis is not None:
            return self._redis

        redis_url = os.getenv("REDIS_URL")
        if not redis_url:
            return None

        try:
            redis = Redis.from_url(redis_url, decode_responses=True)
            await redis.ping()
        except Exception:
            return None

        self._redis = redis
        return self._redis

    async def _close_redis(self) -> None:
        if self._redis is None:
            return
        with suppress(Exception):
            await self._redis.aclose()
        self._redis = None

    @staticmethod
    def _channel(topology_id: str) -> str:
        return f"sim:{topology_id}:events"

manager = ConnectionManager()
