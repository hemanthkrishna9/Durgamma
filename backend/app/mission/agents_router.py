"""Agent API routes."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.db.models import Agent
from app.schemas import AgentResponse

router = APIRouter(prefix="/api/agents", tags=["agents"])


@router.get("", response_model=list[AgentResponse])
async def list_agents(
    mission_id: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    stmt = select(Agent)
    if mission_id:
        stmt = stmt.where(Agent.mission_id == mission_id)
    stmt = stmt.order_by(Agent.authority_level.desc())
    result = await db.execute(stmt)
    return list(result.scalars().all())


@router.get("/{agent_id}", response_model=AgentResponse)
async def get_agent(agent_id: str, db: AsyncSession = Depends(get_db)):
    agent = await db.get(Agent, agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    return agent
