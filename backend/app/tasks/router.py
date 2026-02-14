"""Task API routes."""

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.db.models import EventType, Mission, Task, TaskDependency, TaskStatus
from app.events.service import log_event, post_activity
from app.schemas import TaskCreate, TaskResponse, TaskUpdate

router = APIRouter(prefix="/api/tasks", tags=["tasks"])


@router.post("", response_model=TaskResponse, status_code=201)
async def create_task(data: TaskCreate, db: AsyncSession = Depends(get_db)):
    mission = await db.get(Mission, data.mission_id)
    if not mission:
        raise HTTPException(status_code=404, detail="Mission not found")

    task = Task(
        id=f"task-{uuid.uuid4().hex[:12]}",
        mission_id=data.mission_id,
        title=data.title,
        description=data.description,
        assignee_role=data.assignee_role,
        dependencies=data.dependencies,
        priority=data.priority,
        requires_approval=data.requires_approval,
        status=TaskStatus.BACKLOG,
    )
    db.add(task)
    await db.flush()

    # Create dependency records
    for dep_id in data.dependencies:
        dep = TaskDependency(task_id=task.id, depends_on_id=dep_id)
        db.add(dep)

    await log_event(
        db, mission.id, EventType.TASK_CREATED,
        message=f"Task created: {task.title}",
        task_id=task.id,
        data={"title": task.title, "assignee_role": task.assignee_role},
    )

    await db.commit()
    await db.refresh(task)
    return task


@router.get("", response_model=list[TaskResponse])
async def list_tasks(
    mission_id: str | None = None,
    status: TaskStatus | None = None,
    assignee_role: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    stmt = select(Task)
    if mission_id:
        stmt = stmt.where(Task.mission_id == mission_id)
    if status:
        stmt = stmt.where(Task.status == status)
    if assignee_role:
        stmt = stmt.where(Task.assignee_role == assignee_role)
    stmt = stmt.order_by(Task.priority.desc(), Task.created_at)
    result = await db.execute(stmt)
    return list(result.scalars().all())


@router.get("/{task_id}", response_model=TaskResponse)
async def get_task(task_id: str, db: AsyncSession = Depends(get_db)):
    task = await db.get(Task, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


@router.patch("/{task_id}", response_model=TaskResponse)
async def update_task(
    task_id: str, data: TaskUpdate, db: AsyncSession = Depends(get_db)
):
    task = await db.get(Task, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    update_data = data.model_dump(exclude_unset=True)
    old_status = task.status

    for field, value in update_data.items():
        setattr(task, field, value)

    if "status" in update_data and update_data["status"] != old_status:
        await log_event(
            db, task.mission_id, EventType.TASK_STATUS_CHANGED,
            message=f"Task '{task.title}': {old_status.value} → {data.status.value}",
            task_id=task.id,
            data={"old_status": old_status.value, "new_status": data.status.value},
        )
        await post_activity(
            db, task.mission_id, "task_update",
            f"Task '{task.title}' moved to {data.status.value}",
        )

    await db.commit()
    await db.refresh(task)
    return task


@router.get("/{task_id}/dependencies-met", response_model=bool)
async def check_dependencies_met(task_id: str, db: AsyncSession = Depends(get_db)):
    """Check if all dependencies for a task are completed."""
    task = await db.get(Task, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    if not task.dependencies:
        return True

    for dep_id in task.dependencies:
        dep_task = await db.get(Task, dep_id)
        if not dep_task or dep_task.status != TaskStatus.DONE:
            return False
    return True
