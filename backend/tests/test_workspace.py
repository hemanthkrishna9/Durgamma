"""Tests for the Workspace Generator."""

import os
import shutil
import tempfile

import pytest

from app.workspace.generator import (
    generate_workspace,
    generate_user_md,
    generate_memory_md,
    _build_mission_context,
    _build_squad_context,
    _build_task_context,
    _render_template,
)
from app.config import settings


@pytest.fixture
def temp_missions_dir():
    """Create a temporary missions directory."""
    tmpdir = tempfile.mkdtemp()
    original = settings.missions_dir
    settings.missions_dir = tmpdir
    yield tmpdir
    settings.missions_dir = original
    shutil.rmtree(tmpdir, ignore_errors=True)


@pytest.fixture
def sample_mission():
    return {
        "title": "Build a Food Delivery App",
        "goal": "Build a food delivery app like UberEats",
        "customer_name": "John Doe",
        "budget_cap": 100.0,
        "specification": "React frontend, Python backend, PostgreSQL database",
    }


@pytest.fixture
def sample_spawn_plan():
    return [
        {"role": "orchestrator", "name": "Orca", "model": "claude-sonnet-4-20250514"},
        {"role": "architect", "name": "Archie", "model": "claude-sonnet-4-20250514"},
        {"role": "backend-dev", "name": "Atlas", "model": "claude-sonnet-4-20250514"},
        {"role": "frontend-dev", "name": "Pixel", "model": "claude-sonnet-4-20250514"},
    ]


@pytest.fixture
def sample_tasks():
    return [
        {
            "title": "Design Architecture",
            "description": "Design the system architecture",
            "assignee_role": "architect",
            "dependencies": [],
        },
        {
            "title": "Build Backend APIs",
            "description": "Implement REST APIs",
            "assignee_role": "backend-dev",
            "dependencies": ["Design Architecture"],
        },
        {
            "title": "Build Frontend",
            "description": "Build React frontend",
            "assignee_role": "frontend-dev",
            "dependencies": ["Design Architecture"],
        },
    ]


def test_build_mission_context(sample_mission):
    ctx = _build_mission_context(sample_mission)
    assert "Food Delivery App" in ctx
    assert "John Doe" in ctx
    assert "UberEats" in ctx


def test_build_squad_context(sample_spawn_plan):
    ctx = _build_squad_context(sample_spawn_plan)
    assert "Orca" in ctx
    assert "Archie" in ctx
    assert "orchestrator" in ctx
    assert "Authority: 100" in ctx


def test_build_task_context(sample_tasks):
    ctx = _build_task_context(sample_tasks, "architect")
    assert "Design Architecture" in ctx
    assert "Build Backend" not in ctx  # not assigned to architect


def test_build_task_context_no_tasks(sample_tasks):
    ctx = _build_task_context(sample_tasks, "devops")
    assert "No tasks assigned" in ctx


def test_render_template():
    template = "Hello {{AGENT_NAME}}, your mission is {{MISSION_CONTEXT}}"
    result = _render_template(template, {
        "AGENT_NAME": "Orca",
        "MISSION_CONTEXT": "Build an app",
    })
    assert "Hello Orca" in result
    assert "Build an app" in result


def test_generate_user_md(sample_mission):
    md = generate_user_md(sample_mission)
    assert "John Doe" in md
    assert "$100.00" in md
    assert "HUMAN_NEEDED" in md


def test_generate_memory_md():
    md = generate_memory_md()
    assert "MEMORY" in md
    assert "Current State" in md


def test_generate_workspace(temp_missions_dir, sample_mission, sample_spawn_plan, sample_tasks):
    paths = generate_workspace("test-mission-001", sample_mission, sample_spawn_plan, sample_tasks)

    assert len(paths) == 4
    assert "orchestrator" in paths
    assert "architect" in paths

    # Check orchestrator workspace
    orch_path = paths["orchestrator"]
    assert os.path.isdir(orch_path)
    assert os.path.isfile(os.path.join(orch_path, "SOUL.md"))
    assert os.path.isfile(os.path.join(orch_path, "IDENTITY.md"))
    assert os.path.isfile(os.path.join(orch_path, "AGENTS.md"))
    assert os.path.isfile(os.path.join(orch_path, "TOOLS.md"))
    assert os.path.isfile(os.path.join(orch_path, "HEARTBEAT.md"))
    assert os.path.isfile(os.path.join(orch_path, "USER.md"))
    assert os.path.isfile(os.path.join(orch_path, "MEMORY.md"))

    # Check content was rendered with context
    soul_content = open(os.path.join(orch_path, "SOUL.md")).read()
    assert "Orchestrator" in soul_content
    assert "Food Delivery" in soul_content

    identity_content = open(os.path.join(orch_path, "IDENTITY.md")).read()
    assert "Orca" in identity_content

    agents_content = open(os.path.join(orch_path, "AGENTS.md")).read()
    assert "Archie" in agents_content  # squad context should include other agents


def test_workspace_shared_dir_created(temp_missions_dir, sample_mission, sample_spawn_plan, sample_tasks):
    generate_workspace("test-mission-002", sample_mission, sample_spawn_plan, sample_tasks)
    shared_path = os.path.join(temp_missions_dir, "test-mission-002", "shared")
    assert os.path.isdir(shared_path)


def test_workspace_idempotent(temp_missions_dir, sample_mission, sample_spawn_plan, sample_tasks):
    """Running generate_workspace twice should not fail."""
    paths1 = generate_workspace("test-mission-003", sample_mission, sample_spawn_plan, sample_tasks)
    paths2 = generate_workspace("test-mission-003", sample_mission, sample_spawn_plan, sample_tasks)
    assert paths1 == paths2
