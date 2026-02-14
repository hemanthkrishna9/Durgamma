"""Mission Control — FastAPI Application Entry Point."""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.db.database import close_db, init_db
from app.approval.router import router as approval_router
from app.cost.router import router as cost_router
from app.events.router import router as events_router
from app.mission.router import router as mission_router
from app.mission.agents_router import router as agents_router
from app.tasks.router import router as tasks_router
from app.conflict.resolver import router as conflict_router
from app.delivery.router import router as delivery_router
from app.websocket import ws_manager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting Mission Control backend...")
    await init_db()
    logger.info("Database initialized")
    yield
    logger.info("Shutting down Mission Control backend...")
    await close_db()


app = FastAPI(
    title=settings.app_name,
    description="AI Agent Squad Platform — Mission Control Backend",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(mission_router)
app.include_router(agents_router)
app.include_router(tasks_router)
app.include_router(approval_router)
app.include_router(cost_router)
app.include_router(conflict_router)
app.include_router(delivery_router)
app.include_router(events_router)


# Health check
@app.get("/api/health")
async def health():
    return {
        "status": "ok",
        "service": settings.app_name,
        "version": "0.1.0",
        "ws_connections": ws_manager.connection_count,
    }


# WebSocket endpoint for dashboard real-time updates
@app.websocket("/ws/{mission_id}")
async def websocket_endpoint(websocket: WebSocket, mission_id: str):
    await ws_manager.connect(websocket, mission_id)
    try:
        while True:
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text('{"type": "pong"}')
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket, mission_id)
