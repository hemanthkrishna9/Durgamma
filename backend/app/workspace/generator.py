"""Workspace Generator — creates agent workspace directories with identity files.

For each agent in a mission, generates a workspace directory containing:
- SOUL.md, IDENTITY.md, AGENTS.md, TOOLS.md, HEARTBEAT.md
- USER.md (customer context)
- MEMORY.md (initially empty, agents update this themselves)

Templates are loaded from agent-templates/ and customized using Jinja2.
"""

import logging
import os
from pathlib import Path
from typing import Any

from jinja2 import Template

from app.config import settings
from app.workspace.registry import registry

logger = logging.getLogger(__name__)

IDENTITY_FILES = ["SOUL.md", "IDENTITY.md", "AGENTS.md", "TOOLS.md", "HEARTBEAT.md"]


def _load_template(role: str, filename: str) -> str | None:
    """Load a template file for a role."""
    template_dir = Path(settings.agent_templates_dir)
    filepath = template_dir / role / filename
    if filepath.exists():
        return filepath.read_text()
    logger.warning(f"Template not found: {filepath}")
    return None


def _render_template(template_str: str, context: dict[str, Any]) -> str:
    """Render a Jinja2-style template with the given context."""
    # Replace our custom placeholders with Jinja2-compatible ones
    jinja_str = template_str
    for key in context:
        placeholder = "{{" + key + "}}"
        jinja_str = jinja_str.replace(placeholder, "{{ " + key + " }}")

    tmpl = Template(jinja_str)
    return tmpl.render(**context)


def _build_squad_context(spawn_plan: list[dict[str, Any]]) -> str:
    """Build the squad context string showing who else is on the team."""
    lines = ["## Your Squad\n"]
    for agent_info in spawn_plan:
        role = agent_info["role"]
        name = agent_info.get("name", role)
        role_data = registry.get_role(role)
        desc = role_data.get("description", "") if role_data else ""
        authority = role_data.get("authority_level", 50) if role_data else 50
        lines.append(f"- **{name}** ({role}) — {desc} [Authority: {authority}]")
    return "\n".join(lines)


def _build_task_context(tasks: list[dict[str, Any]], agent_role: str) -> str:
    """Build the task context for a specific agent."""
    my_tasks = [t for t in tasks if t.get("assignee_role") == agent_role]
    if not my_tasks:
        return "## Assigned Tasks\n\nNo tasks assigned yet. Check the task board."

    lines = ["## Assigned Tasks\n"]
    for task in my_tasks:
        deps = task.get("dependencies", [])
        dep_str = f" (depends on: {', '.join(deps)})" if deps else ""
        lines.append(f"- **{task['title']}**: {task.get('description', '')}{dep_str}")
    return "\n".join(lines)


def _build_mission_context(mission: dict[str, Any]) -> str:
    """Build the mission context string."""
    return f"""## Mission Context

**Mission**: {mission.get('title', 'Unnamed Mission')}
**Goal**: {mission.get('goal', 'No goal specified')}
**Customer**: {mission.get('customer_name', 'Anonymous')}
**Specification**: {mission.get('specification', 'No detailed specification yet.')}
"""


def generate_user_md(mission: dict[str, Any]) -> str:
    """Generate USER.md with customer context."""
    return f"""# USER — Customer Context

## Customer
**Name**: {mission.get('customer_name', 'Anonymous')}

## Mission
**Goal**: {mission.get('goal', '')}

## Preferences & Constraints
{mission.get('specification', 'No specific preferences or constraints provided.')}

## Budget
**Budget Cap**: ${mission.get('budget_cap', 0):.2f}

## Communication
- Post updates to the activity feed
- Escalate decisions with [HUMAN_NEEDED] tag
- The customer sees the task board and activity feed on the dashboard
"""


def generate_memory_md() -> str:
    """Generate initial MEMORY.md (empty, agents populate this)."""
    return """# MEMORY

## Current State
No tasks started yet.

## Key Decisions
(none yet)

## Progress
(none yet)

---
*This file is updated by the agent itself after each heartbeat cycle.*
"""


def generate_workspace(
    mission_id: str,
    mission: dict[str, Any],
    spawn_plan: list[dict[str, Any]],
    tasks: list[dict[str, Any]],
) -> dict[str, str]:
    """Generate workspace directories for all agents in the spawn plan.

    Args:
        mission_id: Unique mission identifier
        mission: Mission data (title, goal, specification, etc.)
        spawn_plan: List of agent configs [{role, name, model, ...}]
        tasks: List of task definitions [{title, description, assignee_role, dependencies}]

    Returns:
        Dictionary mapping agent role to workspace path.
    """
    missions_dir = Path(settings.missions_dir)
    base_dir = missions_dir / mission_id
    shared_dir = base_dir / "shared"

    # Create shared directory
    shared_dir.mkdir(parents=True, exist_ok=True)

    # Build common context
    mission_context = _build_mission_context(mission)
    squad_context = _build_squad_context(spawn_plan)
    user_md = generate_user_md(mission)
    memory_md = generate_memory_md()

    workspace_paths = {}

    for agent_info in spawn_plan:
        role = agent_info["role"]
        name = agent_info.get("name", role.title())

        # Create workspace directory
        workspace_dir = base_dir / role
        workspace_dir.mkdir(parents=True, exist_ok=True)

        # Build per-agent context
        task_context = _build_task_context(tasks, role)
        context = {
            "MISSION_CONTEXT": mission_context,
            "SQUAD_CONTEXT": squad_context,
            "TASK_CONTEXT": task_context,
            "AGENT_NAME": name,
        }

        # Generate identity files from templates
        for filename in IDENTITY_FILES:
            template_str = _load_template(role, filename)
            if template_str:
                content = _render_template(template_str, context)
            else:
                content = f"# {filename.replace('.md', '')} — {name}\n\n(Template not found for role: {role})\n"

            filepath = workspace_dir / filename
            filepath.write_text(content)

        # Write USER.md and MEMORY.md
        (workspace_dir / "USER.md").write_text(user_md)
        (workspace_dir / "MEMORY.md").write_text(memory_md)

        workspace_paths[role] = str(workspace_dir)
        logger.info(f"Generated workspace for {role} ({name}) at {workspace_dir}")

    return workspace_paths
