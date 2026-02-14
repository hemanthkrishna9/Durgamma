"""WebSocket manager for real-time dashboard updates."""

import json
import logging
from typing import Any

from fastapi import WebSocket

logger = logging.getLogger(__name__)


class ConnectionManager:
    """Manages WebSocket connections for real-time dashboard updates."""

    def __init__(self):
        self._connections: dict[str, list[WebSocket]] = {}  # mission_id -> connections

    async def connect(self, websocket: WebSocket, mission_id: str) -> None:
        await websocket.accept()
        if mission_id not in self._connections:
            self._connections[mission_id] = []
        self._connections[mission_id].append(websocket)
        logger.info(f"WebSocket connected for mission {mission_id}")

    def disconnect(self, websocket: WebSocket, mission_id: str) -> None:
        if mission_id in self._connections:
            self._connections[mission_id] = [
                ws for ws in self._connections[mission_id] if ws != websocket
            ]
            if not self._connections[mission_id]:
                del self._connections[mission_id]
        logger.info(f"WebSocket disconnected for mission {mission_id}")

    async def broadcast(self, mission_id: str, event_type: str, data: dict[str, Any]) -> None:
        """Broadcast an event to all connections watching a mission."""
        message = json.dumps({"type": event_type, "data": data})
        if mission_id not in self._connections:
            return

        dead = []
        for ws in self._connections[mission_id]:
            try:
                await ws.send_text(message)
            except Exception:
                dead.append(ws)

        for ws in dead:
            self._connections[mission_id].remove(ws)

    async def broadcast_all(self, event_type: str, data: dict[str, Any]) -> None:
        """Broadcast to all connections across all missions."""
        message = json.dumps({"type": event_type, "data": data})
        for mission_id in list(self._connections.keys()):
            dead = []
            for ws in self._connections[mission_id]:
                try:
                    await ws.send_text(message)
                except Exception:
                    dead.append(ws)
            for ws in dead:
                self._connections[mission_id].remove(ws)

    @property
    def connection_count(self) -> int:
        return sum(len(conns) for conns in self._connections.values())


# Singleton
ws_manager = ConnectionManager()
