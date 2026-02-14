"""Task Progression Service — automatically moves tasks through the pipeline.

Simulates agent work by progressing tasks based on dependency resolution
and time-based transitions:

1. BACKLOG -> TODO: when all dependencies are met
2. TODO -> IN_PROGRESS: agent picks up the task
3. IN_PROGRESS -> REVIEW: after simulated work duration
4. REVIEW -> DONE: after brief review period
5. Updates agent status (active <-> working) accordingly
"""

import asyncio
import logging
import random
from datetime import datetime, timezone, timedelta

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.db.models import (
    Agent,
    AgentStatus,
    EventType,
    Mission,
    MissionStatus,
    Task,
    TaskStatus,
)
from app.events.service import log_event, post_activity
from app.tasks.dependencies import are_dependencies_met
from app.websocket import ws_manager

logger = logging.getLogger(__name__)

# How often the progression loop runs (seconds)
TICK_INTERVAL = 15

# Simulated work durations (seconds) — tasks spend this long in each stage
WORK_DURATION = timedelta(seconds=45)   # time in IN_PROGRESS before -> REVIEW
REVIEW_DURATION = timedelta(seconds=30)  # time in REVIEW before -> DONE


class TaskProgressionService:
    """Background service that progresses tasks through the pipeline."""

    def __init__(self):
        self._running = False
        self._task: asyncio.Task | None = None

    async def start(self, session_factory: async_sessionmaker) -> None:
        if self._running:
            return
        self._running = True
        self._task = asyncio.create_task(self._run_loop(session_factory))
        logger.info("Task progression service started")

    async def stop(self) -> None:
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None
        logger.info("Task progression service stopped")

    @property
    def is_running(self) -> bool:
        return self._running

    async def _run_loop(self, session_factory: async_sessionmaker) -> None:
        while self._running:
            try:
                async with session_factory() as db:
                    await self._tick(db)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Task progression error: {e}")
            await asyncio.sleep(TICK_INTERVAL)

    async def _tick(self, db: AsyncSession) -> None:
        """One progression tick — advance tasks where possible."""
        # Find all executing missions
        result = await db.execute(
            select(Mission).where(Mission.status == MissionStatus.EXECUTING)
        )
        missions = list(result.scalars().all())

        for mission in missions:
            await self._progress_mission(db, mission.id)

        await db.commit()

    async def _progress_mission(self, db: AsyncSession, mission_id: str) -> None:
        """Progress all tasks for a single mission."""
        now = datetime.now(timezone.utc)

        # Load all agents for this mission
        result = await db.execute(
            select(Agent).where(Agent.mission_id == mission_id)
        )
        agents = list(result.scalars().all())

        # Auto-activate agents stuck in initializing (no gateway needed)
        for agent in agents:
            if agent.status == AgentStatus.INITIALIZING:
                agent.status = AgentStatus.ACTIVE
                agent.last_heartbeat = now
                await log_event(
                    db, mission_id, EventType.AGENT_STATUS_CHANGED,
                    message=f"{agent.name} is now active and ready",
                    agent_id=agent.id,
                    data={"old": "initializing", "new": "active"},
                )
                await ws_manager.broadcast(mission_id, "agent_status_changed", {
                    "agent_id": agent.id,
                    "agent_name": agent.name,
                    "role": agent.role,
                    "status": "active",
                })
                logger.info(f"Agent {agent.name} ({agent.role}) auto-activated")

        agents_by_role: dict[str, list[Agent]] = {}
        for agent in agents:
            agents_by_role.setdefault(agent.role, []).append(agent)

        # Load all tasks for this mission
        result = await db.execute(
            select(Task).where(Task.mission_id == mission_id)
        )
        tasks = list(result.scalars().all())

        for task in tasks:
            await self._progress_task(db, task, agents_by_role, now, mission_id)

    async def _progress_task(
        self,
        db: AsyncSession,
        task: Task,
        agents_by_role: dict[str, list[Agent]],
        now: datetime,
        mission_id: str,
    ) -> None:
        """Try to advance a single task one step."""

        # BACKLOG -> TODO: when dependencies are met
        if task.status == TaskStatus.BACKLOG:
            if await are_dependencies_met(db, task):
                task.status = TaskStatus.TODO
                task.progress = "Dependencies met — ready to start"
                await self._log_transition(db, task, "backlog", "todo", mission_id)
            return

        # TODO -> IN_PROGRESS: assign to an available agent
        if task.status == TaskStatus.TODO:
            agent = self._find_available_agent(task, agents_by_role)
            if agent:
                task.status = TaskStatus.IN_PROGRESS
                task.assignee_agent_id = agent.id
                task.progress = f"Agent {agent.name} started working"
                task.updated_at = now
                agent.status = AgentStatus.WORKING
                agent.current_task_id = task.id
                await self._log_transition(
                    db, task, "todo", "in_progress", mission_id, agent
                )
            return

        # IN_PROGRESS -> REVIEW: after work duration
        if task.status == TaskStatus.IN_PROGRESS:
            elapsed = now - (task.updated_at or now)
            if elapsed >= WORK_DURATION:
                task.status = TaskStatus.REVIEW
                task.progress = "Work complete — under review"
                task.updated_at = now
                await self._log_transition(
                    db, task, "in_progress", "review", mission_id
                )
            elif not task.progress or "working" not in task.progress.lower():
                # Update progress messages to show activity
                messages = [
                    f"Implementing {task.title.lower()}...",
                    "Writing code and running tests...",
                    "Making progress on implementation...",
                    "Building and validating changes...",
                ]
                task.progress = random.choice(messages)
            return

        # REVIEW -> DONE: after review duration
        if task.status == TaskStatus.REVIEW:
            elapsed = now - (task.updated_at or now)
            if elapsed >= REVIEW_DURATION:
                task.status = TaskStatus.DONE
                task.progress = "Completed successfully"
                task.output = f"{task.title} delivered"
                task.updated_at = now

                # Free up the agent
                await self._release_agent(db, task)

                await self._log_transition(
                    db, task, "review", "done", mission_id
                )
            return

    def _find_available_agent(
        self, task: Task, agents_by_role: dict[str, list[Agent]]
    ) -> Agent | None:
        """Find an available agent for a task.

        First checks if the task already has a pre-assigned agent (from mission
        spawn). Falls back to finding any available agent with matching role.
        """
        # Check pre-assigned agent first
        if task.assignee_agent_id:
            for agents in agents_by_role.values():
                for agent in agents:
                    if agent.id == task.assignee_agent_id and agent.status == AgentStatus.ACTIVE:
                        return agent

        # Fall back to role-based matching
        role = task.assignee_role
        if not role:
            return None

        candidates = agents_by_role.get(role, [])
        for agent in candidates:
            if agent.status == AgentStatus.ACTIVE:
                return agent
        return None

    async def _release_agent(self, db: AsyncSession, task: Task) -> None:
        """Release the agent assigned to a completed task."""
        if not task.assignee_agent_id:
            return
        agent = await db.get(Agent, task.assignee_agent_id)
        if agent and agent.status == AgentStatus.WORKING:
            agent.status = AgentStatus.ACTIVE
            agent.current_task_id = None

    async def _log_transition(
        self,
        db: AsyncSession,
        task: Task,
        old_status: str,
        new_status: str,
        mission_id: str,
        agent: Agent | None = None,
    ) -> None:
        """Log a task status transition as an event + activity entry."""
        await log_event(
            db,
            mission_id,
            EventType.TASK_STATUS_CHANGED,
            message=f"Task '{task.title}': {old_status} -> {new_status}",
            task_id=task.id,
            agent_id=agent.id if agent else None,
            data={"old_status": old_status, "new_status": new_status},
        )
        agent_name = agent.name if agent else "System"
        await post_activity(
            db,
            mission_id,
            "task_update",
            f"Task '{task.title}' moved to {new_status}",
            agent_name=agent_name,
            agent_role=agent.role if agent else "orchestrator",
        )

        # Broadcast via WebSocket for real-time UI updates
        await ws_manager.broadcast(mission_id, "task_status_changed", {
            "task_id": task.id,
            "title": task.title,
            "old_status": old_status,
            "new_status": new_status,
            "agent_name": agent_name,
        })

        logger.info(f"Task '{task.title}' [{old_status} -> {new_status}]")


# Singleton
progression_service = TaskProgressionService()
