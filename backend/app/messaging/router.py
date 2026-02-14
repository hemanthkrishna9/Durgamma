"""Agent messaging API routes."""

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.messaging.service import (
    acknowledge_message,
    broadcast_to_squad,
    get_messages,
    get_unread_count,
    send_message,
)

router = APIRouter(prefix="/api/messages", tags=["messages"])


class SendMessageRequest(BaseModel):
    mission_id: str
    from_agent_id: str
    to_agent_id: str
    content: str
    message_type: str = "general"
    data: dict | None = None


class BroadcastRequest(BaseModel):
    mission_id: str
    from_agent_id: str
    content: str
    message_type: str = "general"


class MessageResponse(BaseModel):
    id: int
    mission_id: str
    from_agent_id: str
    to_agent_id: str
    message_type: str
    content: str
    data: dict
    acknowledged: bool
    created_at: str

    model_config = {"from_attributes": True}


@router.post("/send")
async def send(data: SendMessageRequest, db: AsyncSession = Depends(get_db)):
    """Send a message between agents."""
    return await send_message(
        db, data.mission_id, data.from_agent_id, data.to_agent_id,
        data.content, data.message_type, data.data,
    )


@router.post("/broadcast")
async def broadcast(data: BroadcastRequest, db: AsyncSession = Depends(get_db)):
    """Broadcast a message to all agents in a mission."""
    return await broadcast_to_squad(
        db, data.mission_id, data.from_agent_id,
        data.content, data.message_type,
    )


@router.get("/{mission_id}")
async def list_messages(
    mission_id: str,
    agent_id: str | None = None,
    message_type: str | None = None,
    limit: int = 50,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
):
    """Get messages for a mission."""
    messages = await get_messages(db, mission_id, agent_id, message_type, limit, offset)
    return [
        {
            "id": m.id,
            "mission_id": m.mission_id,
            "from_agent_id": m.from_agent_id,
            "to_agent_id": m.to_agent_id,
            "message_type": m.message_type,
            "content": m.content,
            "data": m.data,
            "acknowledged": m.acknowledged,
            "created_at": m.created_at.isoformat(),
        }
        for m in messages
    ]


@router.post("/{message_id}/acknowledge")
async def ack_message(message_id: int, db: AsyncSession = Depends(get_db)):
    """Acknowledge receipt of a message."""
    return await acknowledge_message(db, message_id)


@router.get("/{mission_id}/unread/{agent_id}")
async def unread_count(
    mission_id: str, agent_id: str, db: AsyncSession = Depends(get_db)
):
    """Get count of unread messages for an agent."""
    count = await get_unread_count(db, mission_id, agent_id)
    return {"agent_id": agent_id, "unread": count}
