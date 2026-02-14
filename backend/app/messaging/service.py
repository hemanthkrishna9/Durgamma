"""Agent-to-Agent Messaging Service.

Enables structured communication between agents:
- Direct messages (agent A → agent B)
- Handoff messages (transfer ownership of a task)
- Escalation messages (request help from higher authority)
- Broadcast messages (agent → all agents in a mission)

Messages are stored in the DB for audit trail and can be
relayed through OpenClaw sessions.
"""

import logging
from typing import Any

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Agent, AgentMessage, EventType
from app.events.service import log_event, post_activity
from app.mission.orchestrator import get_gateway_client
from app.websocket import ws_manager

logger = logging.getLogger(__name__)


async def send_message(
    db: AsyncSession,
    mission_id: str,
    from_agent_id: str,
    to_agent_id: str,
    content: str,
    message_type: str = "general",
    data: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Send a message from one agent to another.

    The message is:
    1. Stored in the database
    2. Relayed to the target agent's OpenClaw session
    3. Broadcast to the dashboard via WebSocket
    4. Logged as an event
    """
    from_agent = await db.get(Agent, from_agent_id)
    to_agent = await db.get(Agent, to_agent_id)

    if not from_agent:
        return {"status": "error", "message": f"Sender agent {from_agent_id} not found"}
    if not to_agent:
        return {"status": "error", "message": f"Recipient agent {to_agent_id} not found"}

    # Store message
    msg = AgentMessage(
        mission_id=mission_id,
        from_agent_id=from_agent_id,
        to_agent_id=to_agent_id,
        message_type=message_type,
        content=content,
        data=data or {},
    )
    db.add(msg)
    await db.flush()

    # Relay through OpenClaw if both agents have sessions
    gateway = get_gateway_client()
    if from_agent.session_id and to_agent.session_id and gateway.connected:
        relay_content = (
            f"[MESSAGE from {from_agent.name} ({from_agent.role})] "
            f"[type: {message_type}] {content}"
        )
        await gateway.agent_message(
            from_agent.session_id, to_agent.session_id, relay_content
        )

    # Log event
    await log_event(
        db, mission_id, EventType.AGENT_MESSAGE,
        message=f"{from_agent.name} → {to_agent.name}: {content[:100]}",
        agent_id=from_agent_id,
        data={
            "from": from_agent_id,
            "to": to_agent_id,
            "type": message_type,
            "content": content,
        },
    )

    # Post to activity feed for handoffs and escalations
    if message_type in ("handoff", "escalation"):
        await post_activity(
            db, mission_id, message_type,
            f"[{message_type.upper()}] {from_agent.name} → {to_agent.name}: {content}",
            agent_id=from_agent_id,
            agent_name=from_agent.name,
            agent_role=from_agent.role,
        )

    # Broadcast to dashboard
    await ws_manager.broadcast(mission_id, "agent_message", {
        "message_id": msg.id,
        "from_agent": {"id": from_agent_id, "name": from_agent.name, "role": from_agent.role},
        "to_agent": {"id": to_agent_id, "name": to_agent.name, "role": to_agent.role},
        "type": message_type,
        "content": content,
    })

    await db.commit()

    return {
        "status": "ok",
        "message_id": msg.id,
        "from": from_agent.name,
        "to": to_agent.name,
    }


async def broadcast_to_squad(
    db: AsyncSession,
    mission_id: str,
    from_agent_id: str,
    content: str,
    message_type: str = "general",
) -> dict[str, Any]:
    """Broadcast a message from one agent to all other agents in the mission."""
    result = await db.execute(
        select(Agent)
        .where(Agent.mission_id == mission_id)
        .where(Agent.id != from_agent_id)
    )
    recipients = list(result.scalars().all())

    sent = 0
    for agent in recipients:
        await send_message(
            db, mission_id, from_agent_id, agent.id,
            content, message_type,
        )
        sent += 1

    return {"status": "ok", "recipients": sent}


async def get_messages(
    db: AsyncSession,
    mission_id: str,
    agent_id: str | None = None,
    message_type: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> list[AgentMessage]:
    """Get messages for a mission, optionally filtered by agent or type."""
    stmt = select(AgentMessage).where(AgentMessage.mission_id == mission_id)

    if agent_id:
        stmt = stmt.where(
            (AgentMessage.from_agent_id == agent_id) |
            (AgentMessage.to_agent_id == agent_id)
        )

    if message_type:
        stmt = stmt.where(AgentMessage.message_type == message_type)

    stmt = stmt.order_by(AgentMessage.created_at.desc()).limit(limit).offset(offset)
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def acknowledge_message(
    db: AsyncSession, message_id: int
) -> dict[str, Any]:
    """Mark a message as acknowledged by the recipient."""
    msg = await db.get(AgentMessage, message_id)
    if not msg:
        return {"status": "error", "message": "Message not found"}

    msg.acknowledged = True
    await db.commit()
    return {"status": "ok", "message_id": message_id}


async def get_unread_count(
    db: AsyncSession, mission_id: str, agent_id: str
) -> int:
    """Get count of unacknowledged messages for an agent."""
    from sqlalchemy import func
    result = await db.execute(
        select(func.count(AgentMessage.id))
        .where(AgentMessage.mission_id == mission_id)
        .where(AgentMessage.to_agent_id == agent_id)
        .where(AgentMessage.acknowledged == False)
    )
    return result.scalar() or 0
