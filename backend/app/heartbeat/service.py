"""Heartbeat Service — monitors agent health and status.

Each agent's OpenClaw session emits a heartbeat at a configurable interval.
This service:
1. Polls agent sessions for status
2. Updates last_heartbeat timestamp
3. Detects stale/unresponsive agents
4. Broadcasts status updates to the dashboard
"""

import asyncio
import logging
from datetime import datetime, timezone, timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.db.models import Agent, AgentStatus, EventType, Mission, MissionStatus
from app.events.service import log_event, post_activity
from app.mission.orchestrator import get_gateway_client
from app.websocket import ws_manager

logger = logging.getLogger(__name__)

# How long before an agent is considered stale (no heartbeat)
STALE_THRESHOLD = timedelta(minutes=5)

# How often to run the heartbeat check loop (seconds)
HEARTBEAT_POLL_INTERVAL = 60


class HeartbeatService:
    """Monitors agent health via periodic polling."""

    def __init__(self):
        self._running = False
        self._task: asyncio.Task | None = None

    async def start(self, session_factory: async_sessionmaker) -> None:
        """Start the heartbeat monitoring loop."""
        if self._running:
            return
        self._running = True
        self._task = asyncio.create_task(self._run_loop(session_factory))
        logger.info("Heartbeat service started")

    async def stop(self) -> None:
        """Stop the heartbeat monitoring loop."""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None
        logger.info("Heartbeat service stopped")

    @property
    def is_running(self) -> bool:
        return self._running

    async def _run_loop(self, session_factory: async_sessionmaker) -> None:
        """Main polling loop."""
        while self._running:
            try:
                async with session_factory() as db:
                    await self._check_all_agents(db)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Heartbeat check error: {e}")

            await asyncio.sleep(HEARTBEAT_POLL_INTERVAL)

    async def _check_all_agents(self, db: AsyncSession) -> None:
        """Check all active agents across all executing missions."""
        # Find all executing missions
        result = await db.execute(
            select(Mission).where(Mission.status == MissionStatus.EXECUTING)
        )
        missions = list(result.scalars().all())

        for mission in missions:
            await self._check_mission_agents(db, mission.id)

    async def _check_mission_agents(self, db: AsyncSession, mission_id: str) -> None:
        """Check all agents for a specific mission."""
        result = await db.execute(
            select(Agent)
            .where(Agent.mission_id == mission_id)
            .where(Agent.status.in_([AgentStatus.ACTIVE, AgentStatus.WORKING]))
        )
        agents = list(result.scalars().all())
        gateway = get_gateway_client()

        now = datetime.now(timezone.utc)

        for agent in agents:
            try:
                status = await self._poll_agent(gateway, agent, now)
                if status:
                    await ws_manager.broadcast(mission_id, "agent_heartbeat", {
                        "agent_id": agent.id,
                        "agent_name": agent.name,
                        "role": agent.role,
                        "status": agent.status.value,
                        "last_heartbeat": now.isoformat(),
                    })
            except Exception as e:
                logger.warning(f"Error polling agent {agent.id}: {e}")

        await db.commit()

    async def _poll_agent(
        self, gateway: Any, agent: Agent, now: datetime
    ) -> dict[str, Any] | None:
        """Poll a single agent's session and update state."""
        if not agent.session_id:
            return None

        session_status = await gateway.get_session_status(agent.session_id)
        if not session_status or session_status.get("status") == "error":
            # Agent session is gone — mark as error
            if agent.status != AgentStatus.ERROR:
                agent.status = AgentStatus.ERROR
                logger.warning(f"Agent {agent.name} ({agent.id}) session not found")
            return None

        # Update heartbeat timestamp
        agent.last_heartbeat = now

        # Check if agent was stale before and is now responsive
        return {
            "agent_id": agent.id,
            "status": agent.status.value,
            "session_active": True,
        }

    async def process_heartbeat(
        self, db: AsyncSession, agent_id: str, data: dict[str, Any]
    ) -> dict[str, Any]:
        """Process an incoming heartbeat from an agent.

        Called when an agent sends a heartbeat message through OpenClaw.
        Updates the agent's last_heartbeat, status, and current task info.
        """
        agent = await db.get(Agent, agent_id)
        if not agent:
            return {"status": "error", "message": "Agent not found"}

        now = datetime.now(timezone.utc)
        agent.last_heartbeat = now

        # Update agent status from heartbeat data
        new_status = data.get("status")
        if new_status and new_status in [s.value for s in AgentStatus]:
            old_status = agent.status
            agent.status = AgentStatus(new_status)
            if old_status != agent.status:
                await log_event(
                    db, agent.mission_id, EventType.AGENT_STATUS_CHANGED,
                    message=f"{agent.name} status: {old_status.value} → {new_status}",
                    agent_id=agent_id,
                    data={"old": old_status.value, "new": new_status},
                )

        # Update current task from heartbeat
        current_task = data.get("current_task_id")
        if current_task:
            agent.current_task_id = current_task

        # Update token usage from heartbeat
        tokens = data.get("tokens_used", 0)
        if tokens > 0:
            agent.tokens_used += tokens

        # Log the heartbeat event
        await log_event(
            db, agent.mission_id, EventType.AGENT_HEARTBEAT,
            message=f"Heartbeat from {agent.name}",
            agent_id=agent_id,
            data=data,
        )

        # Broadcast to dashboard
        await ws_manager.broadcast(agent.mission_id, "agent_heartbeat", {
            "agent_id": agent_id,
            "agent_name": agent.name,
            "role": agent.role,
            "status": agent.status.value,
            "last_heartbeat": now.isoformat(),
            "current_task_id": agent.current_task_id,
        })

        await db.commit()

        return {"status": "ok", "agent_id": agent_id}

    async def get_stale_agents(
        self, db: AsyncSession, mission_id: str
    ) -> list[dict[str, Any]]:
        """Find agents that haven't sent a heartbeat recently."""
        cutoff = datetime.now(timezone.utc) - STALE_THRESHOLD

        result = await db.execute(
            select(Agent)
            .where(Agent.mission_id == mission_id)
            .where(Agent.status.in_([AgentStatus.ACTIVE, AgentStatus.WORKING]))
            .where(
                (Agent.last_heartbeat < cutoff) | (Agent.last_heartbeat.is_(None))
            )
        )
        stale = list(result.scalars().all())

        return [
            {
                "agent_id": a.id,
                "name": a.name,
                "role": a.role,
                "last_heartbeat": a.last_heartbeat.isoformat() if a.last_heartbeat else None,
                "status": a.status.value,
            }
            for a in stale
        ]


# Singleton
heartbeat_service = HeartbeatService()
