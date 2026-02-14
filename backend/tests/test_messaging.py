"""Tests for Agent-to-Agent messaging."""

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


async def _setup_mission_with_agents(client: AsyncClient) -> tuple[str, list[dict]]:
    """Create a mission with agents."""
    resp = await client.post("/api/missions", json={
        "title": "Messaging Test",
        "goal": "Build a web application",
    })
    mission_id = resp.json()["id"]

    await client.patch(f"/api/missions/{mission_id}", json={
        "specification": "React + Python FastAPI + PostgreSQL",
        "budget_cap": 100.0,
    })
    await client.post(f"/api/missions/{mission_id}/analyze")
    await client.post(f"/api/missions/{mission_id}/approve")

    resp = await client.get(f"/api/agents?mission_id={mission_id}")
    return mission_id, resp.json()


async def test_send_message(client: AsyncClient):
    """Test sending a message between two agents."""
    mission_id, agents = await _setup_mission_with_agents(client)
    agent_a = agents[0]
    agent_b = agents[1]

    resp = await client.post("/api/messages/send", json={
        "mission_id": mission_id,
        "from_agent_id": agent_a["id"],
        "to_agent_id": agent_b["id"],
        "content": "Please review the API design",
        "message_type": "request",
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert "message_id" in data


async def test_send_message_invalid_agent(client: AsyncClient):
    """Test sending a message to nonexistent agent."""
    mission_id, agents = await _setup_mission_with_agents(client)

    resp = await client.post("/api/messages/send", json={
        "mission_id": mission_id,
        "from_agent_id": agents[0]["id"],
        "to_agent_id": "nonexistent",
        "content": "Hello",
    })
    assert resp.status_code == 200
    assert resp.json()["status"] == "error"


async def test_list_messages(client: AsyncClient):
    """Test listing messages for a mission."""
    mission_id, agents = await _setup_mission_with_agents(client)
    agent_a = agents[0]
    agent_b = agents[1]

    # Send a message
    await client.post("/api/messages/send", json={
        "mission_id": mission_id,
        "from_agent_id": agent_a["id"],
        "to_agent_id": agent_b["id"],
        "content": "Test message",
    })

    # List all messages
    resp = await client.get(f"/api/messages/{mission_id}")
    assert resp.status_code == 200
    messages = resp.json()
    assert len(messages) >= 1
    assert messages[0]["content"] == "Test message"


async def test_list_messages_filtered_by_agent(client: AsyncClient):
    """Test listing messages filtered by a specific agent."""
    mission_id, agents = await _setup_mission_with_agents(client)
    agent_a = agents[0]
    agent_b = agents[1]

    await client.post("/api/messages/send", json={
        "mission_id": mission_id,
        "from_agent_id": agent_a["id"],
        "to_agent_id": agent_b["id"],
        "content": "Message 1",
    })

    # Filter by agent_a — should appear (as sender)
    resp = await client.get(f"/api/messages/{mission_id}?agent_id={agent_a['id']}")
    assert resp.status_code == 200
    assert len(resp.json()) >= 1


async def test_acknowledge_message(client: AsyncClient):
    """Test acknowledging a message."""
    mission_id, agents = await _setup_mission_with_agents(client)

    # Send a message
    resp = await client.post("/api/messages/send", json={
        "mission_id": mission_id,
        "from_agent_id": agents[0]["id"],
        "to_agent_id": agents[1]["id"],
        "content": "Ack test",
    })
    msg_id = resp.json()["message_id"]

    # Acknowledge
    resp = await client.post(f"/api/messages/{msg_id}/acknowledge")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


async def test_unread_count(client: AsyncClient):
    """Test getting unread message count for an agent."""
    mission_id, agents = await _setup_mission_with_agents(client)
    agent_a = agents[0]
    agent_b = agents[1]

    # Send two messages to agent_b
    for i in range(2):
        await client.post("/api/messages/send", json={
            "mission_id": mission_id,
            "from_agent_id": agent_a["id"],
            "to_agent_id": agent_b["id"],
            "content": f"Message {i+1}",
        })

    resp = await client.get(f"/api/messages/{mission_id}/unread/{agent_b['id']}")
    assert resp.status_code == 200
    assert resp.json()["unread"] == 2


async def test_broadcast_to_squad(client: AsyncClient):
    """Test broadcasting a message to all agents."""
    mission_id, agents = await _setup_mission_with_agents(client)
    sender = agents[0]

    resp = await client.post("/api/messages/broadcast", json={
        "mission_id": mission_id,
        "from_agent_id": sender["id"],
        "content": "Team update: architecture review complete",
        "message_type": "general",
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    # Should have sent to all other agents
    assert data["recipients"] == len(agents) - 1
