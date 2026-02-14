"""Events and Activity Feed API routes."""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.db.models import EventType
from app.events.service import get_activity_feed, get_events
from app.schemas import ActivityEntryResponse, EventResponse

router = APIRouter(prefix="/api", tags=["events"])


@router.get("/events/{mission_id}", response_model=list[EventResponse])
async def list_events(
    mission_id: str,
    event_type: EventType | None = None,
    limit: int = 100,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
):
    events = await get_events(db, mission_id, event_type, limit, offset)
    return events


@router.get("/activity/{mission_id}", response_model=list[ActivityEntryResponse])
async def list_activity(
    mission_id: str,
    limit: int = 50,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
):
    entries = await get_activity_feed(db, mission_id, limit, offset)
    return entries
