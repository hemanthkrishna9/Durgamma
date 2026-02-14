"""Tests for the Mission Orchestrator — full lifecycle test."""

import shutil
import tempfile

import pytest
from httpx import AsyncClient

from app.config import settings


@pytest.fixture(autouse=True)
def temp_missions_dir():
    tmpdir = tempfile.mkdtemp()
    original = settings.missions_dir
    settings.missions_dir = tmpdir
    yield tmpdir
    settings.missions_dir = original
    shutil.rmtree(tmpdir, ignore_errors=True)


async def _create_and_analyze_mission(client: AsyncClient) -> str:
    """Helper: create a mission, add spec, and analyze it."""
    resp = await client.post("/api/missions", json={
        "title": "Build a Food Delivery App",
        "goal": "Build a food delivery web application",
    })
    mission_id = resp.json()["id"]

    await client.patch(f"/api/missions/{mission_id}", json={
        "specification": "React frontend, Python FastAPI backend, PostgreSQL. For restaurants.",
        "budget_cap": 200.0,
    })

    await client.post(f"/api/missions/{mission_id}/analyze")
    return mission_id


async def test_approve_and_spawn(client: AsyncClient):
    """Test the full approve → spawn → agents created → tasks created flow."""
    mission_id = await _create_and_analyze_mission(client)

    # Approve the mission
    resp = await client.post(f"/api/missions/{mission_id}/approve")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert data["agents_created"] >= 4
    assert data["tasks_created"] >= 3

    # Check mission is now executing
    resp = await client.get(f"/api/missions/{mission_id}")
    assert resp.json()["status"] == "executing"

    # Check agents were created
    resp = await client.get(f"/api/agents?mission_id={mission_id}")
    assert resp.status_code == 200
    agents = resp.json()
    assert len(agents) >= 4

    roles = [a["role"] for a in agents]
    assert "orchestrator" in roles
    assert "architect" in roles

    # All agents should be active
    for agent in agents:
        assert agent["status"] == "active"

    # Check tasks were created
    resp = await client.get(f"/api/tasks?mission_id={mission_id}")
    tasks = resp.json()
    assert len(tasks) >= 3

    # Tasks without deps should be todo, tasks with deps should be backlog
    has_todo = any(t["status"] == "todo" for t in tasks)
    has_backlog = any(t["status"] == "backlog" for t in tasks)
    assert has_todo  # at least one task with no deps
    assert has_backlog  # at least one task with deps


async def test_approve_requires_planning_status(client: AsyncClient):
    """Can't approve a mission that hasn't been analyzed."""
    resp = await client.post("/api/missions", json={
        "title": "Not Analyzed",
        "goal": "A goal",
    })
    mission_id = resp.json()["id"]

    resp = await client.post(f"/api/missions/{mission_id}/approve")
    assert resp.status_code == 400


async def test_pause_and_resume_agents(client: AsyncClient):
    mission_id = await _create_and_analyze_mission(client)
    await client.post(f"/api/missions/{mission_id}/approve")

    # Pause
    resp = await client.post(f"/api/missions/{mission_id}/pause")
    assert resp.status_code == 200
    assert resp.json()["agents_paused"] >= 4

    # All agents should be sleeping
    resp = await client.get(f"/api/agents?mission_id={mission_id}")
    for agent in resp.json():
        assert agent["status"] == "sleeping"

    # Resume
    resp = await client.post(f"/api/missions/{mission_id}/resume")
    assert resp.status_code == 200
    assert resp.json()["agents_resumed"] >= 4


async def test_terminate_mission(client: AsyncClient):
    mission_id = await _create_and_analyze_mission(client)
    await client.post(f"/api/missions/{mission_id}/approve")

    # Terminate
    resp = await client.post(f"/api/missions/{mission_id}/terminate")
    assert resp.status_code == 200
    assert resp.json()["agents_terminated"] >= 4

    # Mission should be closed
    resp = await client.get(f"/api/missions/{mission_id}")
    assert resp.json()["status"] == "closed"


async def test_events_logged_during_spawn(client: AsyncClient):
    mission_id = await _create_and_analyze_mission(client)
    await client.post(f"/api/missions/{mission_id}/approve")

    resp = await client.get(f"/api/events/{mission_id}")
    events = resp.json()
    event_types = [e["event_type"] for e in events]

    assert "agent_spawned" in event_types
    assert "task_created" in event_types


async def test_activity_feed_during_spawn(client: AsyncClient):
    mission_id = await _create_and_analyze_mission(client)
    await client.post(f"/api/missions/{mission_id}/approve")

    resp = await client.get(f"/api/activity/{mission_id}")
    entries = resp.json()
    assert any("agents spawned" in e["content"] for e in entries)


async def test_full_lifecycle(client: AsyncClient):
    """End-to-end test: create → analyze → approve → check → terminate."""
    # Create
    resp = await client.post("/api/missions", json={
        "title": "E2E Test Mission",
        "goal": "Build a web application for project management",
    })
    mission_id = resp.json()["id"]
    assert resp.json()["status"] == "intake"

    # Add specification
    await client.patch(f"/api/missions/{mission_id}", json={
        "specification": "React + Python FastAPI + PostgreSQL. Target: small teams.",
        "budget_cap": 150.0,
    })

    # Analyze
    resp = await client.post(f"/api/missions/{mission_id}/analyze")
    assert resp.status_code == 200
    plan = resp.json()
    assert len(plan["agents"]) >= 4

    # Check status is planning
    resp = await client.get(f"/api/missions/{mission_id}")
    assert resp.json()["status"] == "planning"

    # Approve
    resp = await client.post(f"/api/missions/{mission_id}/approve")
    assert resp.status_code == 200

    # Verify agents
    resp = await client.get(f"/api/agents?mission_id={mission_id}")
    agents = resp.json()
    assert len(agents) >= 4

    # Verify tasks
    resp = await client.get(f"/api/tasks?mission_id={mission_id}")
    tasks = resp.json()
    assert len(tasks) >= 3

    # Check dependency graph
    for task in tasks:
        if task["dependencies"]:
            # Each dependency should be a valid task ID
            task_ids = [t["id"] for t in tasks]
            for dep in task["dependencies"]:
                assert dep in task_ids

    # Terminate
    resp = await client.post(f"/api/missions/{mission_id}/terminate")
    assert resp.json()["status"] == "ok"

    resp = await client.get(f"/api/missions/{mission_id}")
    assert resp.json()["status"] == "closed"
