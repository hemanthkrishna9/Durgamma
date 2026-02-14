"""Mission Orchestrator — manages the full lifecycle of a mission.

Handles: approval → agent spawn → task creation → execution monitoring.
"""

import logging
import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.db.models import (
    Agent,
    AgentStatus,
    Approval,
    ApprovalStatus,
    EventType,
    Mission,
    MissionStatus,
    Task,
    TaskDependency,
    TaskStatus,
)
from app.events.service import log_event, post_activity
from app.openclaw.client import MockOpenClawClient, OpenClawClient
from app.workspace.generator import generate_workspace
from app.workspace.registry import registry

logger = logging.getLogger(__name__)

# Use mock client by default (real client used when Gateway is running)
_gateway_client: OpenClawClient | None = None


def get_gateway_client() -> OpenClawClient:
    global _gateway_client
    if _gateway_client is None:
        _gateway_client = MockOpenClawClient()
    return _gateway_client


def set_gateway_client(client: OpenClawClient) -> None:
    global _gateway_client
    _gateway_client = client


async def approve_and_spawn_mission(
    db: AsyncSession, mission_id: str
) -> dict[str, Any]:
    """Approve a mission plan and spawn all agents.

    This is the key transition from planning → executing.
    1. Generates workspace directories for all agents
    2. Creates agent records in the database
    3. Creates task records with dependencies
    4. Tells OpenClaw Gateway to create sessions
    5. Updates mission status to executing
    """
    mission = await db.get(Mission, mission_id)
    if not mission:
        raise ValueError(f"Mission {mission_id} not found")

    if mission.status not in (MissionStatus.PLANNING, MissionStatus.APPROVED):
        raise ValueError(f"Mission must be in planning/approved status, got {mission.status}")

    spawn_plan = mission.spawn_plan
    if not spawn_plan or "agents" not in spawn_plan:
        raise ValueError("Mission has no spawn plan. Run analyze first.")

    agent_configs = spawn_plan["agents"]
    task_configs = spawn_plan["tasks"]

    # 1. Generate workspace directories
    mission_data = {
        "title": mission.title,
        "goal": mission.goal,
        "specification": mission.specification or "",
        "customer_name": mission.customer_name,
        "budget_cap": mission.budget_cap,
    }
    workspace_paths = generate_workspace(
        mission_id, mission_data, agent_configs, task_configs
    )

    # 2. Create agent records
    created_agents = {}
    gateway = get_gateway_client()
    if not gateway.connected:
        await gateway.connect()

    for agent_config in agent_configs:
        role = agent_config["role"]
        name = agent_config.get("name", role.title())
        model = agent_config.get("model", settings.default_model)
        authority = agent_config.get("authority_level", 50)

        agent_id = f"agent-{uuid.uuid4().hex[:12]}"
        agent = Agent(
            id=agent_id,
            mission_id=mission_id,
            role=role,
            name=name,
            authority_level=authority,
            model=model,
            workspace_path=workspace_paths.get(role, ""),
            status=AgentStatus.INITIALIZING,
        )
        db.add(agent)
        created_agents[role] = agent

        await log_event(
            db, mission_id, EventType.AGENT_SPAWNED,
            message=f"Agent spawned: {name} ({role})",
            agent_id=agent_id,
            data={"role": role, "name": name, "model": model},
        )

    await db.flush()

    # 3. Create task records with dependencies
    title_to_id = {}
    for task_config in task_configs:
        task_id = f"task-{uuid.uuid4().hex[:12]}"
        title = task_config["title"]
        title_to_id[title] = task_id

    for task_config in task_configs:
        title = task_config["title"]
        task_id = title_to_id[title]

        # Resolve dependency titles to task IDs
        dep_ids = []
        for dep_title in task_config.get("dependencies", []):
            if dep_title in title_to_id:
                dep_ids.append(title_to_id[dep_title])

        # Find the agent for this role
        assignee_role = task_config.get("assignee_role", "")
        assignee_agent = created_agents.get(assignee_role)

        task = Task(
            id=task_id,
            mission_id=mission_id,
            title=title,
            description=task_config.get("description", ""),
            assignee_role=assignee_role,
            assignee_agent_id=assignee_agent.id if assignee_agent else None,
            dependencies=dep_ids,
            priority=task_config.get("priority", 0),
            requires_approval=task_config.get("requires_approval", False),
            status=TaskStatus.TODO if not dep_ids else TaskStatus.BACKLOG,
        )
        db.add(task)

        # Create dependency records
        for dep_id in dep_ids:
            db.add(TaskDependency(task_id=task_id, depends_on_id=dep_id))

        await log_event(
            db, mission_id, EventType.TASK_CREATED,
            message=f"Task created: {title}",
            task_id=task_id,
            data={"title": title, "assignee_role": assignee_role},
        )

    # 4. Create OpenClaw sessions for each agent
    for role, agent in created_agents.items():
        tools = registry.get_tools(role)
        session_result = await gateway.create_session(
            session_id=agent.id,
            workspace_path=agent.workspace_path,
            model=agent.model,
            heartbeat_interval=900,  # 15 minutes
            tools=tools,
        )
        if session_result and session_result.get("status") == "ok":
            agent.session_id = agent.id
            agent.status = AgentStatus.ACTIVE
        else:
            agent.status = AgentStatus.ERROR
            logger.error(f"Failed to create session for {role}: {session_result}")

    # 5. Update mission status
    mission.status = MissionStatus.EXECUTING

    await post_activity(
        db, mission_id, "system",
        f"Mission approved! {len(created_agents)} agents spawned, {len(task_configs)} tasks created.",
    )

    await db.commit()

    return {
        "status": "ok",
        "agents_created": len(created_agents),
        "tasks_created": len(task_configs),
        "workspace_paths": workspace_paths,
    }


async def terminate_mission(db: AsyncSession, mission_id: str) -> dict[str, Any]:
    """Terminate all agents and close a mission."""
    mission = await db.get(Mission, mission_id)
    if not mission:
        raise ValueError(f"Mission {mission_id} not found")

    gateway = get_gateway_client()

    # Get all agents for this mission
    result = await db.execute(
        select(Agent).where(Agent.mission_id == mission_id)
    )
    agents = list(result.scalars().all())

    terminated = 0
    for agent in agents:
        if agent.session_id and agent.status != AgentStatus.TERMINATED:
            await gateway.destroy_session(agent.session_id)
            agent.status = AgentStatus.TERMINATED
            terminated += 1

    mission.status = MissionStatus.CLOSED

    await log_event(
        db, mission_id, EventType.MISSION_STATUS_CHANGED,
        message=f"Mission closed. {terminated} agents terminated.",
    )
    await post_activity(
        db, mission_id, "system",
        f"Mission closed. {terminated} agents terminated.",
    )

    await db.commit()

    return {"status": "ok", "agents_terminated": terminated}


async def pause_all_agents(db: AsyncSession, mission_id: str) -> int:
    """Pause all agents for a mission (e.g., budget exceeded)."""
    gateway = get_gateway_client()

    result = await db.execute(
        select(Agent)
        .where(Agent.mission_id == mission_id)
        .where(Agent.status.in_([AgentStatus.ACTIVE, AgentStatus.WORKING, AgentStatus.SLEEPING]))
    )
    agents = list(result.scalars().all())

    paused = 0
    for agent in agents:
        if agent.session_id:
            await gateway.pause_session(agent.session_id)
            agent.status = AgentStatus.SLEEPING
            paused += 1

    await db.commit()
    return paused


async def resume_all_agents(db: AsyncSession, mission_id: str) -> int:
    """Resume all paused agents for a mission."""
    gateway = get_gateway_client()

    result = await db.execute(
        select(Agent)
        .where(Agent.mission_id == mission_id)
        .where(Agent.status == AgentStatus.SLEEPING)
    )
    agents = list(result.scalars().all())

    resumed = 0
    for agent in agents:
        if agent.session_id:
            await gateway.resume_session(agent.session_id)
            agent.status = AgentStatus.ACTIVE
            resumed += 1

    await db.commit()
    return resumed
