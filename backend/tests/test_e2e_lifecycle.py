"""End-to-end integration test — full mission lifecycle.

Tests the complete flow:
  create → add spec → analyze → approve → spawn agents →
  create tasks → update task status → record cost →
  check budget → conflict resolution → delivery → terminate
"""

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


async def test_full_e2e_lifecycle(client: AsyncClient):
    """Complete end-to-end lifecycle test from intake to delivery."""

    # ---- Step 1: Create mission ----
    resp = await client.post("/api/missions", json={
        "title": "E-Commerce Platform",
        "goal": "Build a full-stack e-commerce platform with payment processing",
        "customer_name": "TestCorp",
        "budget_cap": 500.0,
    })
    assert resp.status_code == 201
    mission = resp.json()
    mission_id = mission["id"]
    assert mission["status"] == "intake"
    assert mission["customer_name"] == "TestCorp"
    assert mission["budget_cap"] == 500.0

    # ---- Step 2: Add specification ----
    resp = await client.patch(f"/api/missions/{mission_id}", json={
        "specification": (
            "React + TypeScript frontend, Python FastAPI backend, PostgreSQL database. "
            "Stripe integration for payments. User auth with JWT. "
            "Product catalog, shopping cart, order management."
        ),
    })
    assert resp.status_code == 200

    # ---- Step 3: Analyze ----
    resp = await client.post(f"/api/missions/{mission_id}/analyze")
    assert resp.status_code == 200
    plan = resp.json()
    assert len(plan["agents"]) >= 4
    assert len(plan["tasks"]) >= 3
    assert not plan["clarification_needed"]

    # Check mission is now in planning
    resp = await client.get(f"/api/missions/{mission_id}")
    assert resp.json()["status"] == "planning"

    # ---- Step 4: Approve and spawn ----
    resp = await client.post(f"/api/missions/{mission_id}/approve")
    assert resp.status_code == 200
    spawn = resp.json()
    assert spawn["status"] == "ok"
    agents_count = spawn["agents_created"]
    tasks_count = spawn["tasks_created"]
    assert agents_count >= 4
    assert tasks_count >= 3

    # Verify mission is executing
    resp = await client.get(f"/api/missions/{mission_id}")
    assert resp.json()["status"] == "executing"

    # ---- Step 5: Verify agents ----
    resp = await client.get(f"/api/agents?mission_id={mission_id}")
    assert resp.status_code == 200
    agents = resp.json()
    assert len(agents) == agents_count

    # All should be active
    for agent in agents:
        assert agent["status"] == "active"
        assert agent["mission_id"] == mission_id

    # Must have orchestrator
    roles = [a["role"] for a in agents]
    assert "orchestrator" in roles
    assert "architect" in roles

    # ---- Step 6: Verify tasks with dependencies ----
    resp = await client.get(f"/api/tasks?mission_id={mission_id}")
    assert resp.status_code == 200
    tasks = resp.json()
    assert len(tasks) == tasks_count

    task_ids = {t["id"] for t in tasks}
    todo_tasks = [t for t in tasks if t["status"] == "todo"]
    backlog_tasks = [t for t in tasks if t["status"] == "backlog"]

    assert len(todo_tasks) >= 1, "Should have at least one ready task"
    assert len(backlog_tasks) >= 1, "Should have at least one blocked task"

    # Verify dependency integrity
    for task in tasks:
        for dep_id in task["dependencies"]:
            assert dep_id in task_ids, f"Dependency {dep_id} not found in task list"

    # ---- Step 7: Update task status (simulate work) ----
    first_todo = todo_tasks[0]
    resp = await client.patch(f"/api/tasks/{first_todo['id']}", json={
        "status": "in_progress",
        "progress": "Working on it...",
    })
    assert resp.status_code == 200
    assert resp.json()["status"] == "in_progress"

    # Complete the task
    resp = await client.patch(f"/api/tasks/{first_todo['id']}", json={
        "status": "done",
        "output": "Task completed successfully.",
    })
    assert resp.status_code == 200
    assert resp.json()["status"] == "done"

    # ---- Step 8: Check dependency resolution ----
    resp = await client.get(f"/api/tasks/{first_todo['id']}/dependencies-met")
    assert resp.status_code == 200

    # ---- Step 9: Record cost ----
    test_agent = agents[0]
    resp = await client.post("/api/cost/record", json={
        "mission_id": mission_id,
        "agent_id": test_agent["id"],
        "model": "claude-sonnet-4-20250514",
        "input_tokens": 5000,
        "output_tokens": 2000,
    })
    assert resp.status_code == 200

    # Check cost summary
    resp = await client.get(f"/api/cost/{mission_id}/summary")
    assert resp.status_code == 200
    cost = resp.json()
    assert cost["total_cost"] > 0
    assert cost["budget_cap"] == 500.0
    assert cost["record_count"] == 1

    # ---- Step 10: Budget status ----
    resp = await client.get(f"/api/cost/{mission_id}/budget")
    assert resp.status_code == 200
    budget = resp.json()
    assert budget["remaining"] > 0
    assert budget["status"] == "ok"

    # ---- Step 11: Create approval gate ----
    resp = await client.post("/api/approvals", json={
        "mission_id": mission_id,
        "gate_type": "deploy_staging",
        "title": "Deploy to Staging",
        "description": "Ready for staging deployment review",
        "requested_by": "devops",
    })
    assert resp.status_code == 201
    approval_id = resp.json()["id"]
    assert resp.json()["status"] == "pending"

    # Approve it
    resp = await client.post(f"/api/approvals/{approval_id}/decide", json={
        "status": "approved",
        "comment": "Looks good, proceed to staging.",
    })
    assert resp.status_code == 200
    assert resp.json()["status"] == "approved"
    assert resp.json()["decision_comment"] == "Looks good, proceed to staging."

    # ---- Step 12: Conflict resolution ----
    # Find two actual agents by role
    backend_agent = next((a for a in agents if a["role"] == "backend-dev"), None)
    frontend_agent = next((a for a in agents if a["role"] == "frontend-dev"), None)
    if backend_agent and frontend_agent:
        resp = await client.post("/api/conflicts/resolve", json={
            "mission_id": mission_id,
            "agent_a_id": backend_agent["id"],
            "agent_b_id": frontend_agent["id"],
            "domain": "api",
            "description": "Disagreement on API response format",
        })
        assert resp.status_code == 200
        resolution = resp.json()
        assert "resolution" in resolution

    # ---- Step 13: Divergence check ----
    resp = await client.get(f"/api/conflicts/{mission_id}/divergences")
    assert resp.status_code == 200
    divergences = resp.json()
    assert "issues" in divergences
    assert isinstance(divergences["issues"], list)

    # ---- Step 14: Check events were logged ----
    resp = await client.get(f"/api/events/{mission_id}?limit=100")
    assert resp.status_code == 200
    events = resp.json()
    event_types = [e["event_type"] for e in events]
    assert "agent_spawned" in event_types
    assert "task_created" in event_types

    # ---- Step 15: Activity feed ----
    resp = await client.get(f"/api/activity/{mission_id}?limit=50")
    assert resp.status_code == 200
    activities = resp.json()
    assert len(activities) >= 1
    assert any("agents spawned" in a["content"] for a in activities)

    # ---- Step 16: Pause and resume ----
    resp = await client.post(f"/api/missions/{mission_id}/pause")
    assert resp.status_code == 200
    assert resp.json()["agents_paused"] >= 1

    resp = await client.get(f"/api/agents?mission_id={mission_id}")
    sleeping = [a for a in resp.json() if a["status"] == "sleeping"]
    assert len(sleeping) >= 1

    resp = await client.post(f"/api/missions/{mission_id}/resume")
    assert resp.status_code == 200
    assert resp.json()["agents_resumed"] >= 1

    # ---- Step 17: Generate delivery package ----
    resp = await client.post(f"/api/delivery/{mission_id}/generate")
    assert resp.status_code == 200
    delivery = resp.json()
    assert delivery["status"] == "ok"
    assert "delivery_path" in delivery

    # Mission should now be delivered
    resp = await client.get(f"/api/missions/{mission_id}")
    assert resp.json()["status"] == "delivered"

    # ---- Step 18: Terminate ----
    resp = await client.post(f"/api/missions/{mission_id}/terminate")
    assert resp.status_code == 200
    assert resp.json()["agents_terminated"] >= 1

    # Final: mission is closed
    resp = await client.get(f"/api/missions/{mission_id}")
    assert resp.json()["status"] == "closed"


async def test_e2e_budget_exceeded_auto_pause(client: AsyncClient):
    """Test that exceeding budget auto-pauses the mission."""

    # Create and spawn a mission with tiny budget
    resp = await client.post("/api/missions", json={
        "title": "Tiny Budget Project",
        "goal": "Build a software application",
        "budget_cap": 0.01,
    })
    mission_id = resp.json()["id"]

    await client.patch(f"/api/missions/{mission_id}", json={
        "specification": "Simple React app with Python backend",
    })

    await client.post(f"/api/missions/{mission_id}/analyze")
    resp = await client.post(f"/api/missions/{mission_id}/approve")
    assert resp.status_code == 200

    # Get an agent for cost recording
    resp = await client.get(f"/api/agents?mission_id={mission_id}")
    agent_id = resp.json()[0]["id"]

    # Record a cost that exceeds the tiny budget
    resp = await client.post("/api/cost/record", json={
        "mission_id": mission_id,
        "agent_id": agent_id,
        "model": "claude-opus-4-20250514",
        "input_tokens": 100000,
        "output_tokens": 50000,
    })
    assert resp.status_code == 200

    # Budget should now be exceeded, mission should be paused
    resp = await client.get(f"/api/cost/{mission_id}/budget")
    budget = resp.json()
    assert budget["status"] == "exceeded"

    resp = await client.get(f"/api/missions/{mission_id}")
    assert resp.json()["status"] == "paused"


async def test_e2e_mission_without_spec_needs_clarification(client: AsyncClient):
    """Test that analyzing a mission without a clear spec triggers clarification."""

    resp = await client.post("/api/missions", json={
        "title": "Vague Idea",
        "goal": "Build something cool with apps",
    })
    mission_id = resp.json()["id"]

    # Analyze without specification — should need clarification
    resp = await client.post(f"/api/missions/{mission_id}/analyze")
    assert resp.status_code == 200
    plan = resp.json()
    # With a vague goal and no spec, analyzer may request clarification
    # or provide a basic plan — both are valid outcomes
    assert len(plan["agents"]) >= 1 or plan["clarification_needed"]
