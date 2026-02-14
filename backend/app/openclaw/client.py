"""OpenClaw Gateway WebSocket Client.

Communicates with the OpenClaw Gateway to manage agent sessions,
heartbeats, and inter-agent messaging.
"""

import asyncio
import json
import logging
from typing import Any, Callable, Coroutine

import websockets
from websockets.exceptions import ConnectionClosed

from app.config import settings

logger = logging.getLogger(__name__)


class OpenClawClient:
    """WebSocket client for the OpenClaw Gateway."""

    def __init__(self, url: str | None = None):
        self.url = url or settings.openclaw_gateway_url
        self._ws: Any = None
        self._connected = False
        self._message_handlers: dict[str, list[Callable]] = {}
        self._pending_responses: dict[str, asyncio.Future] = {}
        self._request_id = 0
        self._listen_task: asyncio.Task | None = None

    @property
    def connected(self) -> bool:
        return self._connected

    async def connect(self) -> bool:
        """Connect to the OpenClaw Gateway."""
        try:
            self._ws = await websockets.connect(self.url)
            self._connected = True
            self._listen_task = asyncio.create_task(self._listen())
            logger.info(f"Connected to OpenClaw Gateway at {self.url}")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to OpenClaw Gateway: {e}")
            self._connected = False
            return False

    async def disconnect(self) -> None:
        """Disconnect from the Gateway."""
        self._connected = False
        if self._listen_task:
            self._listen_task.cancel()
            try:
                await self._listen_task
            except asyncio.CancelledError:
                pass
        if self._ws:
            await self._ws.close()
            self._ws = None
        logger.info("Disconnected from OpenClaw Gateway")

    def _next_id(self) -> str:
        self._request_id += 1
        return f"req-{self._request_id}"

    async def _send(self, message: dict[str, Any]) -> dict[str, Any] | None:
        """Send a message and wait for a response."""
        if not self.connected:
            logger.warning("Not connected to Gateway, attempting reconnect...")
            if not await self.connect():
                return None

        request_id = self._next_id()
        message["id"] = request_id

        future: asyncio.Future = asyncio.get_event_loop().create_future()
        self._pending_responses[request_id] = future

        try:
            await self._ws.send(json.dumps(message))
            result = await asyncio.wait_for(future, timeout=30.0)
            return result
        except asyncio.TimeoutError:
            logger.error(f"Timeout waiting for response to {message.get('type')}")
            self._pending_responses.pop(request_id, None)
            return None
        except ConnectionClosed:
            logger.error("Connection closed while waiting for response")
            self._connected = False
            self._pending_responses.pop(request_id, None)
            return None

    async def _listen(self) -> None:
        """Listen for incoming messages from the Gateway."""
        try:
            while self._connected and self._ws:
                raw = await self._ws.recv()
                message = json.loads(raw)

                # Check if this is a response to a pending request
                msg_id = message.get("id")
                if msg_id and msg_id in self._pending_responses:
                    self._pending_responses.pop(msg_id).set_result(message)
                    continue

                # Otherwise dispatch to registered handlers
                msg_type = message.get("type", "")
                for handler in self._message_handlers.get(msg_type, []):
                    asyncio.create_task(handler(message))

        except ConnectionClosed:
            logger.warning("WebSocket connection closed")
            self._connected = False
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error(f"Error in WebSocket listener: {e}")
            self._connected = False

    def on(self, event_type: str, handler: Callable[..., Coroutine]) -> None:
        """Register a handler for a specific message type."""
        if event_type not in self._message_handlers:
            self._message_handlers[event_type] = []
        self._message_handlers[event_type].append(handler)

    # --- Session Management ---

    async def create_session(
        self,
        session_id: str,
        workspace_path: str,
        model: str = "claude-sonnet-4-20250514",
        heartbeat_interval: int = 900,  # 15 minutes in seconds
        tools: list[str] | None = None,
    ) -> dict[str, Any] | None:
        """Create a new agent session."""
        return await self._send({
            "type": "sessions_create",
            "session_id": session_id,
            "workspace": workspace_path,
            "model": model,
            "heartbeat_interval": heartbeat_interval,
            "tools": tools or ["shell", "file", "git"],
        })

    async def destroy_session(self, session_id: str) -> dict[str, Any] | None:
        """Destroy an agent session."""
        return await self._send({
            "type": "sessions_destroy",
            "session_id": session_id,
        })

    async def send_to_session(
        self, session_id: str, message: str
    ) -> dict[str, Any] | None:
        """Send a message to a specific agent session."""
        return await self._send({
            "type": "sessions_send",
            "session_id": session_id,
            "message": message,
        })

    async def spawn_sub_agent(
        self,
        parent_session_id: str,
        child_session_id: str,
        workspace_path: str,
        model: str = "claude-sonnet-4-20250514",
    ) -> dict[str, Any] | None:
        """Spawn a sub-agent from a parent session."""
        return await self._send({
            "type": "sessions_spawn",
            "parent_session_id": parent_session_id,
            "child_session_id": child_session_id,
            "workspace": workspace_path,
            "model": model,
        })

    async def get_session_status(self, session_id: str) -> dict[str, Any] | None:
        """Get the status of an agent session."""
        return await self._send({
            "type": "sessions_status",
            "session_id": session_id,
        })

    async def list_sessions(self) -> dict[str, Any] | None:
        """List all active sessions."""
        return await self._send({
            "type": "sessions_list",
        })

    async def update_heartbeat_interval(
        self, session_id: str, interval: int
    ) -> dict[str, Any] | None:
        """Update the heartbeat interval for a session."""
        return await self._send({
            "type": "sessions_config",
            "session_id": session_id,
            "heartbeat_interval": interval,
        })

    async def pause_session(self, session_id: str) -> dict[str, Any] | None:
        """Pause a session's heartbeat (set interval to 0)."""
        return await self.update_heartbeat_interval(session_id, 0)

    async def resume_session(
        self, session_id: str, interval: int = 900
    ) -> dict[str, Any] | None:
        """Resume a paused session."""
        return await self.update_heartbeat_interval(session_id, interval)

    # --- Agent-to-Agent Communication ---

    async def agent_message(
        self,
        from_session: str,
        to_session: str,
        message: str,
    ) -> dict[str, Any] | None:
        """Send a message between agents."""
        return await self._send({
            "type": "agent_to_agent",
            "from": from_session,
            "to": to_session,
            "message": message,
        })


class MockOpenClawClient(OpenClawClient):
    """Mock client for testing without a real Gateway."""

    def __init__(self):
        super().__init__(url="ws://mock:18789")
        self._sessions: dict[str, dict[str, Any]] = {}
        self._messages: list[dict[str, Any]] = []

    async def connect(self) -> bool:
        self._connected = True
        logger.info("Mock OpenClaw client connected")
        return True

    async def disconnect(self) -> None:
        self._connected = False

    async def _send(self, message: dict[str, Any]) -> dict[str, Any]:
        self._messages.append(message)
        msg_type = message.get("type", "")

        if msg_type == "sessions_create":
            sid = message["session_id"]
            self._sessions[sid] = {
                "session_id": sid,
                "status": "active",
                "workspace": message.get("workspace", ""),
                "model": message.get("model", ""),
            }
            return {"status": "ok", "session_id": sid}

        elif msg_type == "sessions_destroy":
            sid = message["session_id"]
            self._sessions.pop(sid, None)
            return {"status": "ok"}

        elif msg_type == "sessions_status":
            sid = message["session_id"]
            session = self._sessions.get(sid)
            if session:
                return {"status": "ok", "session": session}
            return {"status": "error", "message": "Session not found"}

        elif msg_type == "sessions_list":
            return {"status": "ok", "sessions": list(self._sessions.values())}

        elif msg_type == "sessions_send":
            return {"status": "ok", "message": "delivered"}

        elif msg_type == "sessions_config":
            sid = message["session_id"]
            if sid in self._sessions:
                self._sessions[sid]["heartbeat_interval"] = message.get("heartbeat_interval")
                return {"status": "ok"}
            return {"status": "error", "message": "Session not found"}

        return {"status": "ok"}
