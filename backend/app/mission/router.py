"""Mission API routes."""

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.db.models import EventType, Mission, MissionStatus
from app.events.service import log_event, post_activity
from app.mission.analyzer import analyze_mission_rules, analyze_mission_llm
from app.mission.orchestrator import (
    approve_and_spawn_mission,
    terminate_mission,
    pause_all_agents,
    resume_all_agents,
)
from app.schemas import (
    MissionClarification,
    MissionCreate,
    MissionPlanResponse,
    MissionResponse,
    MissionUpdate,
)

router = APIRouter(prefix="/api/missions", tags=["missions"])


@router.post("", response_model=MissionResponse, status_code=201)
async def create_mission(data: MissionCreate, db: AsyncSession = Depends(get_db)):
    mission = Mission(
        id=f"mission-{uuid.uuid4().hex[:12]}",
        title=data.title,
        goal=data.goal,
        customer_name=data.customer_name,
        budget_cap=data.budget_cap,
        status=MissionStatus.INTAKE,
    )
    db.add(mission)
    await db.flush()

    await log_event(
        db,
        mission.id,
        EventType.MISSION_CREATED,
        message=f"Mission created: {mission.title}",
        data={"title": mission.title, "goal": mission.goal},
    )
    await post_activity(
        db, mission.id, "system", f"Mission '{mission.title}' created"
    )

    await db.commit()
    await db.refresh(mission)
    return mission


@router.get("", response_model=list[MissionResponse])
async def list_missions(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Mission).order_by(Mission.created_at.desc()))
    return list(result.scalars().all())


@router.get("/{mission_id}", response_model=MissionResponse)
async def get_mission(mission_id: str, db: AsyncSession = Depends(get_db)):
    mission = await db.get(Mission, mission_id)
    if not mission:
        raise HTTPException(status_code=404, detail="Mission not found")
    return mission


@router.patch("/{mission_id}", response_model=MissionResponse)
async def update_mission(
    mission_id: str, data: MissionUpdate, db: AsyncSession = Depends(get_db)
):
    mission = await db.get(Mission, mission_id)
    if not mission:
        raise HTTPException(status_code=404, detail="Mission not found")

    update_data = data.model_dump(exclude_unset=True)
    old_status = mission.status

    for field, value in update_data.items():
        setattr(mission, field, value)

    if "status" in update_data and update_data["status"] != old_status:
        await log_event(
            db,
            mission.id,
            EventType.MISSION_STATUS_CHANGED,
            message=f"Mission status: {old_status.value} → {data.status.value}",
            data={"old_status": old_status.value, "new_status": data.status.value},
        )
        await post_activity(
            db, mission.id, "status_change",
            f"Mission status changed to {data.status.value}",
        )

    await db.commit()
    await db.refresh(mission)
    return mission


@router.post("/{mission_id}/analyze", response_model=MissionPlanResponse)
async def analyze_mission(mission_id: str, db: AsyncSession = Depends(get_db)):
    """Analyze a mission and generate a spawn plan + task graph."""
    mission = await db.get(Mission, mission_id)
    if not mission:
        raise HTTPException(status_code=404, detail="Mission not found")

    result = await analyze_mission_llm(mission.goal, mission.specification)

    # Store spawn plan on mission
    mission.spawn_plan = result
    if not result.get("clarification_needed"):
        mission.status = MissionStatus.PLANNING

    await db.commit()
    await db.refresh(mission)

    return MissionPlanResponse(
        mission_id=mission_id,
        agents=result.get("agents", []),
        tasks=result.get("tasks", []),
        estimated_cost=result.get("estimated_cost", {}),
        clarification_needed=result.get("clarification_needed", False),
        questions=result.get("questions", []),
    )


@router.post("/{mission_id}/clarify")
async def clarify_mission(
    mission_id: str, data: MissionClarification, db: AsyncSession = Depends(get_db)
):
    """Submit answers to clarification questions."""
    mission = await db.get(Mission, mission_id)
    if not mission:
        raise HTTPException(status_code=404, detail="Mission not found")

    # Append answers to specification
    answers_text = "\n".join(f"- {q}: {a}" for q, a in data.answers.items())
    mission.specification = (mission.specification or "") + "\n\n## Clarifications\n" + answers_text

    await db.commit()
    await db.refresh(mission)
    return {"status": "ok", "message": "Clarifications received. Re-analyze to update plan."}


@router.post("/{mission_id}/approve")
async def approve_mission(mission_id: str, db: AsyncSession = Depends(get_db)):
    """Approve mission plan and spawn all agents."""
    try:
        result = await approve_and_spawn_mission(db, mission_id)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{mission_id}/terminate")
async def terminate_mission_route(mission_id: str, db: AsyncSession = Depends(get_db)):
    """Terminate all agents and close the mission."""
    try:
        result = await terminate_mission(db, mission_id)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{mission_id}/pause")
async def pause_mission(mission_id: str, db: AsyncSession = Depends(get_db)):
    """Pause all agents."""
    count = await pause_all_agents(db, mission_id)
    return {"status": "ok", "agents_paused": count}


@router.post("/{mission_id}/resume")
async def resume_mission(mission_id: str, db: AsyncSession = Depends(get_db)):
    """Resume all paused agents."""
    count = await resume_all_agents(db, mission_id)
    return {"status": "ok", "agents_resumed": count}


@router.delete("/{mission_id}", status_code=204)
async def delete_mission(mission_id: str, db: AsyncSession = Depends(get_db)):
    mission = await db.get(Mission, mission_id)
    if not mission:
        raise HTTPException(status_code=404, detail="Mission not found")
    await db.delete(mission)
    await db.commit()
