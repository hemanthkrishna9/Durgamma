"""Tests for the Mission Analyzer."""

import pytest
from httpx import AsyncClient

from app.mission.analyzer import analyze_mission_rules


def test_software_mission():
    result = analyze_mission_rules("Build me a todo app with React and Python")
    agents = [a["role"] for a in result["agents"]]

    assert "orchestrator" in agents
    assert "architect" in agents
    assert "backend-dev" in agents
    assert "frontend-dev" in agents
    assert "qa" in agents
    assert "devops" in agents
    assert len(result["tasks"]) >= 5
    assert result["estimated_cost"]["num_agents"] >= 6


def test_business_mission_with_seo():
    result = analyze_mission_rules("Grow my SaaS business with SEO and content marketing")
    agents = [a["role"] for a in result["agents"]]

    assert "orchestrator" in agents
    assert "seo" in agents
    assert "content-writer" in agents
    assert "researcher" in agents


def test_mobile_mission():
    result = analyze_mission_rules("Build a mobile app for food delivery with React Native")
    agents = [a["role"] for a in result["agents"]]

    assert "mobile-dev" in agents
    assert "architect" in agents


def test_data_mission():
    result = analyze_mission_rules(
        "Build a data analytics dashboard with ML predictions"
    )
    agents = [a["role"] for a in result["agents"]]

    assert "analytics" in agents
    assert "ml-engineer" in agents


def test_vague_mission_needs_clarification():
    result = analyze_mission_rules("Help me with my thing")
    assert result["clarification_needed"] is True
    assert len(result["questions"]) > 0


def test_task_dependencies_correct():
    result = analyze_mission_rules("Build a web application")
    tasks = result["tasks"]

    # Find tasks by title
    task_map = {t["title"]: t for t in tasks}

    # Backend should depend on architecture
    if "Build Backend APIs" in task_map:
        assert "Design System Architecture" in task_map["Build Backend APIs"]["dependencies"]

    # Integration should depend on both frontend and backend
    if "Integrate Frontend and Backend" in task_map:
        deps = task_map["Integrate Frontend and Backend"]["dependencies"]
        assert "Build Backend APIs" in deps
        assert "Build Frontend UI" in deps

    # Deploy should require approval
    if "Deploy to Staging" in task_map:
        assert task_map["Deploy to Staging"]["requires_approval"] is True


def test_cost_estimation():
    result = analyze_mission_rules("Build a web application")
    cost = result["estimated_cost"]

    assert "min" in cost
    assert "max" in cost
    assert cost["min"] > 0
    assert cost["max"] > cost["min"]
    assert cost["num_agents"] > 0


def test_design_mission():
    result = analyze_mission_rules(
        "Build a web app with great UI design and mockups"
    )
    agents = [a["role"] for a in result["agents"]]
    assert "designer" in agents

    # Frontend should depend on UI/UX Design
    tasks = result["tasks"]
    task_map = {t["title"]: t for t in tasks}
    if "Build Frontend UI" in task_map:
        assert "UI/UX Design" in task_map["Build Frontend UI"]["dependencies"]


def test_orchestrator_always_spawned():
    result1 = analyze_mission_rules("Build an app")
    result2 = analyze_mission_rules("Grow my business with SEO")
    result3 = analyze_mission_rules("Something vague")

    for result in [result1, result2, result3]:
        agents = [a["role"] for a in result["agents"]]
        assert "orchestrator" in agents


# --- API Integration Tests ---

async def test_analyze_mission_api(client: AsyncClient):
    # Create a mission with specification so it doesn't need clarification
    resp = await client.post("/api/missions", json={
        "title": "Build Todo App",
        "goal": "Build a full-stack todo application with React frontend and Python backend",
    })
    mission_id = resp.json()["id"]

    # Add specification so clarification is not needed
    await client.patch(f"/api/missions/{mission_id}", json={
        "specification": "Web platform using React and Python FastAPI. Target users: developers.",
    })

    # Analyze it
    resp = await client.post(f"/api/missions/{mission_id}/analyze")
    assert resp.status_code == 200
    data = resp.json()

    assert data["mission_id"] == mission_id
    assert len(data["agents"]) >= 4
    assert len(data["tasks"]) >= 3
    assert "estimated_cost" in data

    # Mission should now be in planning status
    resp = await client.get(f"/api/missions/{mission_id}")
    assert resp.json()["status"] == "planning"


async def test_clarify_mission_api(client: AsyncClient):
    resp = await client.post("/api/missions", json={
        "title": "Vague Mission",
        "goal": "Help me with my thing",
    })
    mission_id = resp.json()["id"]

    resp = await client.post(f"/api/missions/{mission_id}/clarify", json={
        "mission_id": mission_id,
        "answers": {
            "What do you want to build?": "A todo app",
            "What platform?": "Web",
        },
    })
    assert resp.status_code == 200

    # Check specification was updated
    resp = await client.get(f"/api/missions/{mission_id}")
    assert "todo app" in resp.json()["specification"]
