"""Task dependency management — checking and resolving dependency graphs."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Task, TaskStatus


async def are_dependencies_met(db: AsyncSession, task: Task) -> bool:
    """Check if all dependencies for a task are completed."""
    if not task.dependencies:
        return True

    for dep_id in task.dependencies:
        dep_task = await db.get(Task, dep_id)
        if not dep_task or dep_task.status != TaskStatus.DONE:
            return False
    return True


async def get_ready_tasks(db: AsyncSession, mission_id: str) -> list[Task]:
    """Get all tasks that are ready to start (deps met, status is backlog/todo)."""
    stmt = (
        select(Task)
        .where(Task.mission_id == mission_id)
        .where(Task.status.in_([TaskStatus.BACKLOG, TaskStatus.TODO]))
        .order_by(Task.priority.desc())
    )
    result = await db.execute(stmt)
    tasks = list(result.scalars().all())

    ready = []
    for task in tasks:
        if await are_dependencies_met(db, task):
            ready.append(task)
    return ready


async def get_blocked_tasks(db: AsyncSession, mission_id: str) -> list[Task]:
    """Get all tasks that are blocked by unmet dependencies."""
    stmt = (
        select(Task)
        .where(Task.mission_id == mission_id)
        .where(Task.status.in_([TaskStatus.BACKLOG, TaskStatus.TODO, TaskStatus.BLOCKED]))
    )
    result = await db.execute(stmt)
    tasks = list(result.scalars().all())

    blocked = []
    for task in tasks:
        if task.dependencies and not await are_dependencies_met(db, task):
            blocked.append(task)
    return blocked


async def get_dependency_graph(db: AsyncSession, mission_id: str) -> dict:
    """Return the full dependency graph for visualization."""
    stmt = select(Task).where(Task.mission_id == mission_id)
    result = await db.execute(stmt)
    tasks = list(result.scalars().all())

    nodes = []
    edges = []
    for task in tasks:
        nodes.append({
            "id": task.id,
            "title": task.title,
            "status": task.status.value,
            "assignee_role": task.assignee_role,
        })
        for dep_id in (task.dependencies or []):
            edges.append({"from": dep_id, "to": task.id})

    return {"nodes": nodes, "edges": edges}
