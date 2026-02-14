"""Delivery API routes."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.delivery.service import generate_delivery_package

router = APIRouter(prefix="/api/delivery", tags=["delivery"])


@router.post("/{mission_id}/generate")
async def generate_delivery(mission_id: str, db: AsyncSession = Depends(get_db)):
    """Generate the delivery package for a mission."""
    try:
        result = await generate_delivery_package(db, mission_id)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
