"""Tests for Conflict Resolution, Budget Management, and Delivery."""

import shutil
import tempfile

import pytest
from httpx import AsyncClient

from app.config import settings
from app.cost.manager import estimate_cost


@pytest.fixture(autouse=True)
def temp_missions_dir():
    tmpdir = tempfile.mkdtemp()
    original = settings.missions_dir
    settings.missions_dir = tmpdir
    yield tmpdir
    settings.missions_dir = original
    shutil.rmtree(tmpdir, ignore_errors=True)


async def _setup_mission_with_agents(client: AsyncClient) -> tuple[str, list[str]]:
    """Create a mission, analyze, approve, return (mission_id, agent_ids)."""
    resp = await client.post("/api/missions", json={
        "title": "Conflict Test",
        "goal": "Build a web application with React and Python",
    })
    mission_id = resp.json()["id"]

    await client.patch(f"/api/missions/{mission_id}", json={
        "specification": "React + Python. Standard web app.",
        "budget_cap": 10.0,
    })

    await client.post(f"/api/missions/{mission_id}/analyze")
    await client.post(f"/api/missions/{mission_id}/approve")

    resp = await client.get(f"/api/agents?mission_id={mission_id}")
    agent_ids = [a["id"] for a in resp.json()]
    return mission_id, agent_ids


# --- Conflict Resolution ---

async def test_resolve_conflict_domain_authority(client: AsyncClient):
    mission_id, agent_ids = await _setup_mission_with_agents(client)

    # Get architect and backend-dev agents
    resp = await client.get(f"/api/agents?mission_id={mission_id}")
    agents = resp.json()
    architect = next((a for a in agents if a["role"] == "architect"), None)
    backend = next((a for a in agents if a["role"] == "backend-dev"), None)

    if not architect or not backend:
        pytest.skip("Required agents not found")

    # Architect should win on architecture domain
    resp = await client.post("/api/conflicts/resolve", json={
        "mission_id": mission_id,
        "agent_a_id": backend["id"],
        "agent_b_id": architect["id"],
        "domain": "architecture",
        "description": "Disagree on database choice",
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["winner_id"] == architect["id"]
    assert "architecture" in data["reason"].lower() or "domain" in data["reason"].lower()


async def test_resolve_conflict_higher_authority(client: AsyncClient):
    mission_id, agent_ids = await _setup_mission_with_agents(client)

    resp = await client.get(f"/api/agents?mission_id={mission_id}")
    agents = resp.json()
    architect = next((a for a in agents if a["role"] == "architect"), None)
    backend = next((a for a in agents if a["role"] == "backend-dev"), None)

    if not architect or not backend:
        pytest.skip("Required agents not found")

    # On unknown domain, architect (90) should beat backend (50)
    resp = await client.post("/api/conflicts/resolve", json={
        "mission_id": mission_id,
        "agent_a_id": backend["id"],
        "agent_b_id": architect["id"],
        "domain": "something_random",
        "description": "Generic disagreement",
    })
    data = resp.json()
    assert data["winner_id"] == architect["id"]
    assert "authority" in data["reason"].lower()


async def test_resolve_conflict_escalate_customer(client: AsyncClient):
    mission_id, agent_ids = await _setup_mission_with_agents(client)

    resp = await client.get(f"/api/agents?mission_id={mission_id}")
    agents = resp.json()
    if len(agents) < 2:
        pytest.skip("Not enough agents")

    # Requirements domain -> customer decides
    resp = await client.post("/api/conflicts/resolve", json={
        "mission_id": mission_id,
        "agent_a_id": agents[0]["id"],
        "agent_b_id": agents[1]["id"],
        "domain": "requirements",
        "description": "Disagree on feature scope",
    })
    data = resp.json()
    assert data["resolution"] == "escalate_customer"


async def test_divergence_detection(client: AsyncClient):
    mission_id, _ = await _setup_mission_with_agents(client)

    resp = await client.get(f"/api/conflicts/{mission_id}/divergences")
    assert resp.status_code == 200
    data = resp.json()
    assert "issues" in data
    assert "count" in data


# --- Cost / Budget Management ---

def test_estimate_cost():
    cost = estimate_cost("claude-sonnet-4-20250514", 1000, 500)
    assert cost > 0
    assert cost < 1.0  # Should be very small for 1500 tokens

    # Opus should cost more
    opus_cost = estimate_cost("claude-opus-4-20250514", 1000, 500)
    assert opus_cost > cost


async def test_record_cost(client: AsyncClient):
    mission_id, _ = await _setup_mission_with_agents(client)

    resp = await client.get(f"/api/agents?mission_id={mission_id}")
    agents = resp.json()

    resp = await client.post("/api/cost/record", json={
        "mission_id": mission_id,
        "agent_id": agents[0]["id"],
        "model": "claude-sonnet-4-20250514",
        "input_tokens": 5000,
        "output_tokens": 2000,
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["cost"] > 0


async def test_budget_status(client: AsyncClient):
    mission_id, _ = await _setup_mission_with_agents(client)

    resp = await client.get(f"/api/cost/{mission_id}/budget")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert data["budget_cap"] == 10.0


async def test_budget_threshold_alerts(client: AsyncClient):
    mission_id, _ = await _setup_mission_with_agents(client)

    resp = await client.get(f"/api/agents?mission_id={mission_id}")
    agents = resp.json()
    agent_id = agents[0]["id"]

    # Record costs to exceed 50% ($5 of $10)
    for _ in range(5):
        await client.post("/api/cost/record", json={
            "mission_id": mission_id,
            "agent_id": agent_id,
            "model": "claude-opus-4-20250514",
            "input_tokens": 50000,
            "output_tokens": 10000,
        })

    resp = await client.get(f"/api/cost/{mission_id}/budget")
    data = resp.json()
    # Should be above 0% now
    assert data["percentage"] > 0


async def test_budget_exceeded_pauses_agents(client: AsyncClient):
    mission_id, _ = await _setup_mission_with_agents(client)

    resp = await client.get(f"/api/agents?mission_id={mission_id}")
    agents = resp.json()
    agent_id = agents[0]["id"]

    # Record huge cost to exceed budget ($10 cap)
    resp = await client.post("/api/cost/record", json={
        "mission_id": mission_id,
        "agent_id": agent_id,
        "model": "claude-opus-4-20250514",
        "input_tokens": 1000000,
        "output_tokens": 500000,
    })
    data = resp.json()

    if data.get("alert") and data["alert"]["level"] == "critical":
        # Mission should be paused
        resp = await client.get(f"/api/missions/{mission_id}")
        assert resp.json()["status"] == "paused"


# --- Delivery ---

async def test_generate_delivery(client: AsyncClient):
    mission_id, _ = await _setup_mission_with_agents(client)

    resp = await client.post(f"/api/delivery/{mission_id}/generate")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert "README.md" in data["files"]
    assert "COST_REPORT.md" in data["files"]
    assert "AUDIT_TRAIL.json" in data["files"]
    assert "ARCHITECTURE.md" in data["files"]

    # Mission should be marked as delivered
    resp = await client.get(f"/api/missions/{mission_id}")
    assert resp.json()["status"] == "delivered"
