"""Heartbeat API routes — agent health monitoring."""

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.heartbeat.service import heartbeat_service

router = APIRouter(prefix="/api/heartbeat", tags=["heartbeat"])


class HeartbeatPayload(BaseModel):
    agent_id: str
    status: str | None = None
    current_task_id: str | None = None
    tokens_used: int = 0
    progress: str = ""


@router.post("/report")
async def report_heartbeat(data: HeartbeatPayload, db: AsyncSession = Depends(get_db)):
    """Receive a heartbeat from an agent."""
    result = await heartbeat_service.process_heartbeat(
        db, data.agent_id, data.model_dump(exclude_unset=True)
    )
    return result


@router.get("/{mission_id}/stale")
async def get_stale_agents(mission_id: str, db: AsyncSession = Depends(get_db)):
    """Get agents that haven't sent a heartbeat recently."""
    stale = await heartbeat_service.get_stale_agents(db, mission_id)
    return {"mission_id": mission_id, "stale_agents": stale, "count": len(stale)}


@router.get("/status")
async def heartbeat_service_status():
    """Check if the heartbeat monitoring service is running."""
    return {"running": heartbeat_service.is_running}
