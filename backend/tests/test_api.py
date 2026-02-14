"""Integration tests for all API endpoints."""

import pytest
from httpx import AsyncClient


# --- Health ---

async def test_health(client: AsyncClient):
    resp = await client.get("/api/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert data["service"] == "Mission Control"


# --- Missions ---

async def test_create_mission(client: AsyncClient):
    resp = await client.post("/api/missions", json={
        "title": "Build a Todo App",
        "goal": "Build a full-stack todo app with React and Python",
        "customer_name": "Test User",
        "budget_cap": 50.0,
    })
    assert resp.status_code == 201
    data = resp.json()
    assert data["title"] == "Build a Todo App"
    assert data["status"] == "intake"
    assert data["budget_cap"] == 50.0
    assert data["cost_spent"] == 0.0
    return data["id"]


async def test_list_missions(client: AsyncClient):
    await client.post("/api/missions", json={
        "title": "Mission 1", "goal": "Goal 1",
    })
    await client.post("/api/missions", json={
        "title": "Mission 2", "goal": "Goal 2",
    })
    resp = await client.get("/api/missions")
    assert resp.status_code == 200
    assert len(resp.json()) == 2


async def test_get_mission(client: AsyncClient):
    create_resp = await client.post("/api/missions", json={
        "title": "Get Test", "goal": "Test goal",
    })
    mission_id = create_resp.json()["id"]

    resp = await client.get(f"/api/missions/{mission_id}")
    assert resp.status_code == 200
    assert resp.json()["title"] == "Get Test"


async def test_get_mission_not_found(client: AsyncClient):
    resp = await client.get("/api/missions/nonexistent")
    assert resp.status_code == 404


async def test_update_mission(client: AsyncClient):
    create_resp = await client.post("/api/missions", json={
        "title": "Update Test", "goal": "Test goal",
    })
    mission_id = create_resp.json()["id"]

    resp = await client.patch(f"/api/missions/{mission_id}", json={
        "status": "planning",
        "budget_cap": 100.0,
    })
    assert resp.status_code == 200
    assert resp.json()["status"] == "planning"
    assert resp.json()["budget_cap"] == 100.0


async def test_delete_mission(client: AsyncClient):
    create_resp = await client.post("/api/missions", json={
        "title": "Delete Test", "goal": "Test goal",
    })
    mission_id = create_resp.json()["id"]

    resp = await client.delete(f"/api/missions/{mission_id}")
    assert resp.status_code == 204

    resp = await client.get(f"/api/missions/{mission_id}")
    assert resp.status_code == 404


# --- Tasks ---

async def _create_mission(client: AsyncClient) -> str:
    resp = await client.post("/api/missions", json={
        "title": "Task Test Mission", "goal": "Testing tasks",
    })
    return resp.json()["id"]


async def test_create_task(client: AsyncClient):
    mission_id = await _create_mission(client)
    resp = await client.post("/api/tasks", json={
        "mission_id": mission_id,
        "title": "Design Architecture",
        "description": "Design the system architecture",
        "assignee_role": "architect",
        "priority": 10,
    })
    assert resp.status_code == 201
    data = resp.json()
    assert data["title"] == "Design Architecture"
    assert data["status"] == "backlog"
    assert data["assignee_role"] == "architect"


async def test_create_task_with_dependencies(client: AsyncClient):
    mission_id = await _create_mission(client)

    t1_resp = await client.post("/api/tasks", json={
        "mission_id": mission_id,
        "title": "Task 1",
        "assignee_role": "architect",
    })
    t1_id = t1_resp.json()["id"]

    t2_resp = await client.post("/api/tasks", json={
        "mission_id": mission_id,
        "title": "Task 2",
        "assignee_role": "backend-dev",
        "dependencies": [t1_id],
    })
    assert t2_resp.status_code == 201
    assert t1_id in t2_resp.json()["dependencies"]


async def test_list_tasks_by_mission(client: AsyncClient):
    mission_id = await _create_mission(client)
    await client.post("/api/tasks", json={
        "mission_id": mission_id, "title": "T1",
    })
    await client.post("/api/tasks", json={
        "mission_id": mission_id, "title": "T2",
    })

    resp = await client.get(f"/api/tasks?mission_id={mission_id}")
    assert resp.status_code == 200
    assert len(resp.json()) == 2


async def test_update_task_status(client: AsyncClient):
    mission_id = await _create_mission(client)
    t_resp = await client.post("/api/tasks", json={
        "mission_id": mission_id, "title": "Status Test",
    })
    task_id = t_resp.json()["id"]

    resp = await client.patch(f"/api/tasks/{task_id}", json={
        "status": "in_progress",
        "progress": "Working on it",
    })
    assert resp.status_code == 200
    assert resp.json()["status"] == "in_progress"
    assert resp.json()["progress"] == "Working on it"


async def test_check_dependencies_met(client: AsyncClient):
    mission_id = await _create_mission(client)

    t1_resp = await client.post("/api/tasks", json={
        "mission_id": mission_id, "title": "Dep Task",
    })
    t1_id = t1_resp.json()["id"]

    t2_resp = await client.post("/api/tasks", json={
        "mission_id": mission_id,
        "title": "Dependent Task",
        "dependencies": [t1_id],
    })
    t2_id = t2_resp.json()["id"]

    # Dependencies not met
    resp = await client.get(f"/api/tasks/{t2_id}/dependencies-met")
    assert resp.json() is False

    # Complete the dependency
    await client.patch(f"/api/tasks/{t1_id}", json={"status": "done"})

    # Dependencies now met
    resp = await client.get(f"/api/tasks/{t2_id}/dependencies-met")
    assert resp.json() is True


# --- Approvals ---

async def test_create_and_decide_approval(client: AsyncClient):
    mission_id = await _create_mission(client)

    # Create approval
    resp = await client.post("/api/approvals", json={
        "mission_id": mission_id,
        "gate_type": "deploy_staging",
        "title": "Deploy to Staging",
        "description": "App is ready for staging",
        "requested_by": "devops",
    })
    assert resp.status_code == 201
    approval_id = resp.json()["id"]
    assert resp.json()["status"] == "pending"

    # Approve it
    resp = await client.post(f"/api/approvals/{approval_id}/decide", json={
        "status": "approved",
        "comment": "Looks good, proceed",
    })
    assert resp.status_code == 200
    assert resp.json()["status"] == "approved"
    assert resp.json()["decision_comment"] == "Looks good, proceed"


async def test_reject_approval(client: AsyncClient):
    mission_id = await _create_mission(client)

    resp = await client.post("/api/approvals", json={
        "mission_id": mission_id,
        "gate_type": "deploy_prod",
        "title": "Deploy to Production",
        "requested_by": "devops",
    })
    approval_id = resp.json()["id"]

    resp = await client.post(f"/api/approvals/{approval_id}/decide", json={
        "status": "rejected",
        "comment": "Not ready yet",
    })
    assert resp.status_code == 200
    assert resp.json()["status"] == "rejected"


async def test_cannot_decide_twice(client: AsyncClient):
    mission_id = await _create_mission(client)

    resp = await client.post("/api/approvals", json={
        "mission_id": mission_id,
        "gate_type": "test",
        "title": "Test Gate",
    })
    approval_id = resp.json()["id"]

    await client.post(f"/api/approvals/{approval_id}/decide", json={
        "status": "approved",
    })

    resp = await client.post(f"/api/approvals/{approval_id}/decide", json={
        "status": "rejected",
    })
    assert resp.status_code == 400


async def test_list_approvals(client: AsyncClient):
    mission_id = await _create_mission(client)

    await client.post("/api/approvals", json={
        "mission_id": mission_id, "gate_type": "test1", "title": "Gate 1",
    })
    await client.post("/api/approvals", json={
        "mission_id": mission_id, "gate_type": "test2", "title": "Gate 2",
    })

    resp = await client.get(f"/api/approvals?mission_id={mission_id}")
    assert resp.status_code == 200
    assert len(resp.json()) == 2

    resp = await client.get("/api/approvals?status=pending")
    assert resp.status_code == 200
    assert len(resp.json()) >= 2


# --- Events & Activity ---

async def test_events_logged_on_mission_create(client: AsyncClient):
    resp = await client.post("/api/missions", json={
        "title": "Events Test", "goal": "Test events",
    })
    mission_id = resp.json()["id"]

    resp = await client.get(f"/api/events/{mission_id}")
    assert resp.status_code == 200
    events = resp.json()
    assert len(events) >= 1
    assert any(e["event_type"] == "mission_created" for e in events)


async def test_activity_feed_on_mission_create(client: AsyncClient):
    resp = await client.post("/api/missions", json={
        "title": "Activity Test", "goal": "Test activity",
    })
    mission_id = resp.json()["id"]

    resp = await client.get(f"/api/activity/{mission_id}")
    assert resp.status_code == 200
    entries = resp.json()
    assert len(entries) >= 1


# --- Cost ---

async def test_cost_summary_empty(client: AsyncClient):
    mission_id = await _create_mission(client)

    resp = await client.get(f"/api/cost/{mission_id}/summary")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_cost"] == 0.0
    assert data["record_count"] == 0
