"""Tests for the Agent Registry."""

import pytest
from app.workspace.registry import AgentRegistry


@pytest.fixture
def registry():
    reg = AgentRegistry()
    reg.load()
    return reg


def test_load_registry(registry):
    assert len(registry.roles) > 0
    assert "orchestrator" in registry.roles
    assert "architect" in registry.roles
    assert "backend-dev" in registry.roles


def test_get_role(registry):
    role = registry.get_role("orchestrator")
    assert role is not None
    assert role["display_name"] == "Orchestrator"
    assert role["authority_level"] == 100
    assert role["domain"] == "process"


def test_get_nonexistent_role(registry):
    assert registry.get_role("nonexistent") is None


def test_always_spawn_roles(registry):
    always = registry.get_always_spawn_roles()
    assert "orchestrator" in always
    assert "backend-dev" not in always


def test_roles_by_category(registry):
    sw_roles = registry.get_roles_by_category("software_development")
    assert "architect" in sw_roles
    assert "backend-dev" in sw_roles
    assert "frontend-dev" in sw_roles
    assert "qa" in sw_roles
    assert "devops" in sw_roles
    assert "orchestrator" not in sw_roles


def test_authority_levels(registry):
    assert registry.get_authority_level("orchestrator") == 100
    assert registry.get_authority_level("architect") == 90
    assert registry.get_authority_level("qa") == 80
    assert registry.get_authority_level("devops") == 60
    assert registry.get_authority_level("backend-dev") == 50
    assert registry.get_authority_level("nonexistent") == 50  # default


def test_get_domain(registry):
    assert registry.get_domain("orchestrator") == "process"
    assert registry.get_domain("architect") == "architecture"
    assert registry.get_domain("qa") == "quality"


def test_get_names(registry):
    names = registry.get_role_names("orchestrator")
    assert len(names) >= 1
    assert "Orca" in names


def test_get_tools(registry):
    tools = registry.get_tools("orchestrator")
    assert "shell" in tools
    assert "file" in tools
    assert "task_board" in tools


def test_list_all_roles(registry):
    roles = registry.list_all_roles()
    assert len(roles) >= 17
    assert "orchestrator" in roles
    assert "designer" in roles


def test_to_summary(registry):
    summary = registry.to_summary()
    assert len(summary) >= 17
    first = summary[0]
    assert "role" in first
    assert "display_name" in first
    assert "category" in first
    assert "description" in first


def test_spawn_conditions(registry):
    conditions = registry.get_spawn_conditions("backend-dev")
    assert "mission_requires_backend" in conditions
