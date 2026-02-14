"""Event sourcing service — logs all system events as immutable records."""

import logging
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import ActivityEntry, Event, EventType

logger = logging.getLogger(__name__)


async def log_event(
    db: AsyncSession,
    mission_id: str,
    event_type: EventType,
    message: str = "",
    agent_id: str | None = None,
    task_id: str | None = None,
    data: dict[str, Any] | None = None,
) -> Event:
    """Create an immutable event record."""
    event = Event(
        mission_id=mission_id,
        event_type=event_type,
        agent_id=agent_id,
        task_id=task_id,
        data=data or {},
        message=message,
    )
    db.add(event)
    await db.flush()
    logger.info(f"Event [{event_type.value}] mission={mission_id}: {message}")
    return event


async def get_events(
    db: AsyncSession,
    mission_id: str,
    event_type: EventType | None = None,
    limit: int = 100,
    offset: int = 0,
) -> list[Event]:
    """Retrieve events for a mission."""
    stmt = select(Event).where(Event.mission_id == mission_id)
    if event_type:
        stmt = stmt.where(Event.event_type == event_type)
    stmt = stmt.order_by(Event.created_at.desc()).limit(limit).offset(offset)
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def post_activity(
    db: AsyncSession,
    mission_id: str,
    entry_type: str,
    content: str,
    agent_id: str | None = None,
    agent_name: str = "",
    agent_role: str = "",
    extra_data: dict[str, Any] | None = None,
) -> ActivityEntry:
    """Post an entry to the activity feed."""
    entry = ActivityEntry(
        mission_id=mission_id,
        agent_id=agent_id,
        agent_name=agent_name,
        agent_role=agent_role,
        entry_type=entry_type,
        content=content,
        extra_data=extra_data or {},
    )
    db.add(entry)
    await db.flush()
    return entry


async def get_activity_feed(
    db: AsyncSession,
    mission_id: str,
    limit: int = 50,
    offset: int = 0,
) -> list[ActivityEntry]:
    """Retrieve activity feed entries for a mission."""
    stmt = (
        select(ActivityEntry)
        .where(ActivityEntry.mission_id == mission_id)
        .order_by(ActivityEntry.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())
