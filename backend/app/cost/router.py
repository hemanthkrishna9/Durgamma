"""Cost tracking API routes."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from pydantic import BaseModel

from app.db.database import get_db
from app.db.models import CostRecord, Mission
from app.cost.manager import record_cost, get_budget_status
from app.schemas import CostRecordResponse, CostSummary

router = APIRouter(prefix="/api/cost", tags=["cost"])


@router.get("/{mission_id}/summary", response_model=CostSummary)
async def get_cost_summary(mission_id: str, db: AsyncSession = Depends(get_db)):
    mission = await db.get(Mission, mission_id)
    if not mission:
        raise HTTPException(status_code=404, detail="Mission not found")

    # Total cost
    total_result = await db.execute(
        select(func.coalesce(func.sum(CostRecord.cost), 0.0))
        .where(CostRecord.mission_id == mission_id)
    )
    total_cost = float(total_result.scalar())

    # Per-agent breakdown
    agent_result = await db.execute(
        select(CostRecord.agent_id, func.sum(CostRecord.cost))
        .where(CostRecord.mission_id == mission_id)
        .where(CostRecord.agent_id.isnot(None))
        .group_by(CostRecord.agent_id)
    )
    per_agent = {row[0]: float(row[1]) for row in agent_result.all()}

    # Per-model breakdown
    model_result = await db.execute(
        select(CostRecord.model, func.sum(CostRecord.cost))
        .where(CostRecord.mission_id == mission_id)
        .group_by(CostRecord.model)
    )
    per_model = {row[0]: float(row[1]) for row in model_result.all()}

    # Record count
    count_result = await db.execute(
        select(func.count(CostRecord.id))
        .where(CostRecord.mission_id == mission_id)
    )
    record_count = count_result.scalar() or 0

    budget_pct = (total_cost / mission.budget_cap * 100) if mission.budget_cap > 0 else 0.0

    return CostSummary(
        mission_id=mission_id,
        total_cost=total_cost,
        budget_cap=mission.budget_cap,
        budget_percentage=round(budget_pct, 2),
        per_agent=per_agent,
        per_model=per_model,
        record_count=record_count,
    )


@router.get("/{mission_id}/records", response_model=list[CostRecordResponse])
async def get_cost_records(
    mission_id: str,
    limit: int = 100,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
):
    stmt = (
        select(CostRecord)
        .where(CostRecord.mission_id == mission_id)
        .order_by(CostRecord.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())


class CostRecordCreate(BaseModel):
    mission_id: str
    agent_id: str | None = None
    model: str
    input_tokens: int
    output_tokens: int
    task_id: str | None = None


@router.post("/record")
async def create_cost_record(data: CostRecordCreate, db: AsyncSession = Depends(get_db)):
    """Record an API call cost and check budget thresholds."""
    result = await record_cost(
        db, data.mission_id, data.agent_id,
        data.model, data.input_tokens, data.output_tokens, data.task_id,
    )
    await db.commit()
    return result


@router.get("/{mission_id}/budget")
async def budget_status(mission_id: str, db: AsyncSession = Depends(get_db)):
    """Get current budget status."""
    return await get_budget_status(db, mission_id)
