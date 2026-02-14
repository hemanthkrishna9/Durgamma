"""Tests for Heartbeat service and API."""

import shutil
import tempfile

import pytest
from httpx import AsyncClient

from app.config import settings
from app.heartbeat.service import HeartbeatService


@pytest.fixture(autouse=True)
def temp_missions_dir():
    tmpdir = tempfile.mkdtemp()
    original = settings.missions_dir
    settings.missions_dir = tmpdir
    yield tmpdir
    settings.missions_dir = original
    shutil.rmtree(tmpdir, ignore_errors=True)


async def _create_executing_mission(client: AsyncClient) -> tuple[str, list[dict]]:
    """Helper: create a mission with agents in executing state."""
    resp = await client.post("/api/missions", json={
        "title": "Heartbeat Test Mission",
        "goal": "Build a web application for testing heartbeats",
    })
    mission_id = resp.json()["id"]

    await client.patch(f"/api/missions/{mission_id}", json={
        "specification": "React + Python FastAPI + PostgreSQL",
        "budget_cap": 100.0,
    })
    await client.post(f"/api/missions/{mission_id}/analyze")
    await client.post(f"/api/missions/{mission_id}/approve")

    resp = await client.get(f"/api/agents?mission_id={mission_id}")
    agents = resp.json()
    return mission_id, agents


async def test_heartbeat_report(client: AsyncClient):
    """Test reporting a heartbeat for an agent."""
    mission_id, agents = await _create_executing_mission(client)
    agent = agents[0]

    resp = await client.post("/api/heartbeat/report", json={
        "agent_id": agent["id"],
        "status": "working",
        "current_task_id": None,
        "tokens_used": 500,
        "progress": "Processing task...",
    })
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


async def test_heartbeat_report_unknown_agent(client: AsyncClient):
    """Test reporting heartbeat for nonexistent agent."""
    resp = await client.post("/api/heartbeat/report", json={
        "agent_id": "nonexistent-agent",
        "status": "active",
    })
    assert resp.status_code == 200
    assert resp.json()["status"] == "error"


async def test_stale_agents(client: AsyncClient):
    """Test getting stale agents (all agents with no heartbeat)."""
    mission_id, agents = await _create_executing_mission(client)

    # All agents are newly created with no heartbeat — they should be stale
    resp = await client.get(f"/api/heartbeat/{mission_id}/stale")
    assert resp.status_code == 200
    data = resp.json()
    assert data["count"] >= 1
    assert len(data["stale_agents"]) >= 1


async def test_heartbeat_service_status(client: AsyncClient):
    """Test heartbeat service status endpoint."""
    resp = await client.get("/api/heartbeat/status")
    assert resp.status_code == 200
    # In test mode, service may or may not be running
    assert "running" in resp.json()


def test_heartbeat_service_lifecycle():
    """Test HeartbeatService can be created."""
    service = HeartbeatService()
    assert not service.is_running
