"""Tests for the OpenClaw Gateway Client (using mock)."""

import pytest
from app.openclaw.client import MockOpenClawClient


@pytest.fixture
async def client():
    c = MockOpenClawClient()
    await c.connect()
    yield c
    await c.disconnect()


async def test_connect(client):
    assert client.connected is True


async def test_create_session(client):
    result = await client.create_session(
        session_id="test-session-1",
        workspace_path="/tmp/workspace",
        model="claude-sonnet-4-20250514",
    )
    assert result["status"] == "ok"
    assert result["session_id"] == "test-session-1"


async def test_get_session_status(client):
    await client.create_session(
        session_id="test-session-2",
        workspace_path="/tmp/workspace",
    )
    result = await client.get_session_status("test-session-2")
    assert result["status"] == "ok"
    assert result["session"]["session_id"] == "test-session-2"


async def test_get_nonexistent_session(client):
    result = await client.get_session_status("nonexistent")
    assert result["status"] == "error"


async def test_list_sessions(client):
    await client.create_session(session_id="s1", workspace_path="/tmp/w1")
    await client.create_session(session_id="s2", workspace_path="/tmp/w2")
    result = await client.list_sessions()
    assert result["status"] == "ok"
    assert len(result["sessions"]) == 2


async def test_destroy_session(client):
    await client.create_session(session_id="s3", workspace_path="/tmp/w3")
    result = await client.destroy_session("s3")
    assert result["status"] == "ok"

    status = await client.get_session_status("s3")
    assert status["status"] == "error"


async def test_send_to_session(client):
    await client.create_session(session_id="s4", workspace_path="/tmp/w4")
    result = await client.send_to_session("s4", "Hello agent")
    assert result["status"] == "ok"


async def test_pause_and_resume_session(client):
    await client.create_session(session_id="s5", workspace_path="/tmp/w5")

    result = await client.pause_session("s5")
    assert result["status"] == "ok"

    result = await client.resume_session("s5", interval=900)
    assert result["status"] == "ok"


async def test_disconnect(client):
    await client.disconnect()
    assert client.connected is False
