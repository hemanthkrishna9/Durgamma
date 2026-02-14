"""Approval gate API routes."""

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.db.models import Approval, ApprovalStatus, EventType, Mission
from app.events.service import log_event, post_activity
from app.schemas import ApprovalCreate, ApprovalDecision, ApprovalResponse

router = APIRouter(prefix="/api/approvals", tags=["approvals"])


@router.post("", response_model=ApprovalResponse, status_code=201)
async def create_approval(data: ApprovalCreate, db: AsyncSession = Depends(get_db)):
    mission = await db.get(Mission, data.mission_id)
    if not mission:
        raise HTTPException(status_code=404, detail="Mission not found")

    approval = Approval(
        id=f"approval-{uuid.uuid4().hex[:12]}",
        mission_id=data.mission_id,
        task_id=data.task_id,
        gate_type=data.gate_type,
        title=data.title,
        description=data.description,
        requested_by=data.requested_by,
        status=ApprovalStatus.PENDING,
    )
    db.add(approval)
    await db.flush()

    await log_event(
        db, mission.id, EventType.APPROVAL_REQUESTED,
        message=f"Approval requested: {approval.title}",
        data={"gate_type": data.gate_type, "requested_by": data.requested_by},
    )
    await post_activity(
        db, mission.id, "approval_request",
        f"[HUMAN_NEEDED] Approval required: {approval.title}",
    )

    await db.commit()
    await db.refresh(approval)
    return approval


@router.get("", response_model=list[ApprovalResponse])
async def list_approvals(
    mission_id: str | None = None,
    status: ApprovalStatus | None = None,
    db: AsyncSession = Depends(get_db),
):
    stmt = select(Approval)
    if mission_id:
        stmt = stmt.where(Approval.mission_id == mission_id)
    if status:
        stmt = stmt.where(Approval.status == status)
    stmt = stmt.order_by(Approval.created_at.desc())
    result = await db.execute(stmt)
    return list(result.scalars().all())


@router.post("/{approval_id}/decide", response_model=ApprovalResponse)
async def decide_approval(
    approval_id: str,
    data: ApprovalDecision,
    db: AsyncSession = Depends(get_db),
):
    approval = await db.get(Approval, approval_id)
    if not approval:
        raise HTTPException(status_code=404, detail="Approval not found")
    if approval.status != ApprovalStatus.PENDING:
        raise HTTPException(status_code=400, detail="Approval already decided")

    approval.status = data.status
    approval.decision_comment = data.comment
    approval.decided_at = datetime.now(timezone.utc)

    await log_event(
        db, approval.mission_id, EventType.APPROVAL_DECIDED,
        message=f"Approval {data.status.value}: {approval.title}",
        data={"status": data.status.value, "comment": data.comment},
    )
    await post_activity(
        db, approval.mission_id, "approval_decision",
        f"Approval '{approval.title}' {data.status.value}",
    )

    await db.commit()
    await db.refresh(approval)
    return approval
