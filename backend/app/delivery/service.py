"""Delivery & Handoff Service.

Generates the final delivery package for a completed mission:
- Source code
- Documentation (README, API docs, architecture)
- Deploy configs (Docker, CI/CD)
- Final cost report
- Audit trail
"""

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.db.models import Agent, CostRecord, Event, Mission, MissionStatus, Task

logger = logging.getLogger(__name__)


async def generate_delivery_package(
    db: AsyncSession, mission_id: str
) -> dict[str, Any]:
    """Generate the full delivery package for a mission.

    Returns paths to generated files and summary info.
    """
    mission = await db.get(Mission, mission_id)
    if not mission:
        raise ValueError(f"Mission {mission_id} not found")

    # Get all related data
    agents_result = await db.execute(
        select(Agent).where(Agent.mission_id == mission_id)
    )
    agents = list(agents_result.scalars().all())

    tasks_result = await db.execute(
        select(Task).where(Task.mission_id == mission_id)
    )
    tasks = list(tasks_result.scalars().all())

    events_result = await db.execute(
        select(Event).where(Event.mission_id == mission_id).order_by(Event.created_at)
    )
    events = list(events_result.scalars().all())

    costs_result = await db.execute(
        select(CostRecord).where(CostRecord.mission_id == mission_id)
    )
    cost_records = list(costs_result.scalars().all())

    # Create delivery directory
    delivery_dir = Path(settings.missions_dir) / mission_id / "delivery"
    delivery_dir.mkdir(parents=True, exist_ok=True)

    # Generate README
    readme = _generate_readme(mission, agents, tasks)
    (delivery_dir / "README.md").write_text(readme)

    # Generate cost report
    cost_report = _generate_cost_report(mission, agents, cost_records)
    (delivery_dir / "COST_REPORT.md").write_text(cost_report)

    # Generate audit trail
    audit_trail = _generate_audit_trail(events)
    (delivery_dir / "AUDIT_TRAIL.json").write_text(json.dumps(audit_trail, indent=2, default=str))

    # Generate architecture summary
    arch_summary = _generate_architecture_summary(mission, tasks, agents)
    (delivery_dir / "ARCHITECTURE.md").write_text(arch_summary)

    # Mark mission as delivered
    mission.status = MissionStatus.DELIVERED

    await db.commit()

    return {
        "status": "ok",
        "mission_id": mission_id,
        "delivery_path": str(delivery_dir),
        "files": [
            "README.md",
            "COST_REPORT.md",
            "AUDIT_TRAIL.json",
            "ARCHITECTURE.md",
        ],
        "summary": {
            "total_tasks": len(tasks),
            "completed_tasks": sum(1 for t in tasks if t.status.value == "done"),
            "total_agents": len(agents),
            "total_cost": sum(c.cost for c in cost_records),
        },
    }


def _generate_readme(mission: Mission, agents: list[Agent], tasks: list[Task]) -> str:
    done = sum(1 for t in tasks if t.status.value == "done")
    agent_list = "\n".join(f"- **{a.name}** ({a.role})" for a in agents)
    task_list = "\n".join(
        f"- [{t.status.value.upper()}] {t.title} ({t.assignee_role})" for t in tasks
    )

    return f"""# {mission.title}

## Mission
{mission.goal}

## Specification
{mission.specification or "No detailed specification."}

## Agent Squad
{agent_list}

## Tasks ({done}/{len(tasks)} completed)
{task_list}

## How to Run
See the project source code in the mission workspace directory.

## Generated
This project was built by an AI Agent Squad via Mission Control.
Generated at: {datetime.now(timezone.utc).isoformat()}
"""


def _generate_cost_report(
    mission: Mission, agents: list[Agent], records: list[CostRecord]
) -> str:
    total = sum(r.cost for r in records)
    total_tokens = sum(r.input_tokens + r.output_tokens for r in records)

    per_agent = {}
    for r in records:
        if r.agent_id:
            per_agent[r.agent_id] = per_agent.get(r.agent_id, 0) + r.cost

    per_model = {}
    for r in records:
        per_model[r.model] = per_model.get(r.model, 0) + r.cost

    agent_map = {a.id: a for a in agents}
    agent_lines = "\n".join(
        f"| {agent_map.get(aid, type('', (), {'name': aid, 'role': '?'})()).name} "
        f"| {agent_map.get(aid, type('', (), {'name': aid, 'role': '?'})()).role} "
        f"| ${cost:.4f} |"
        for aid, cost in sorted(per_agent.items(), key=lambda x: -x[1])
    )

    model_lines = "\n".join(
        f"| {model} | ${cost:.4f} |"
        for model, cost in sorted(per_model.items(), key=lambda x: -x[1])
    )

    return f"""# Cost Report — {mission.title}

## Summary
- **Total Cost**: ${total:.4f}
- **Budget Cap**: ${mission.budget_cap:.2f}
- **Budget Used**: {(total / mission.budget_cap * 100) if mission.budget_cap > 0 else 0:.1f}%
- **Total Tokens**: {total_tokens:,}
- **API Calls**: {len(records)}

## Per Agent
| Agent | Role | Cost |
|-------|------|------|
{agent_lines}

## Per Model
| Model | Cost |
|-------|------|
{model_lines}

Generated at: {datetime.now(timezone.utc).isoformat()}
"""


def _generate_audit_trail(events: list[Event]) -> list[dict[str, Any]]:
    return [
        {
            "id": e.id,
            "type": e.event_type.value,
            "agent_id": e.agent_id,
            "task_id": e.task_id,
            "message": e.message,
            "data": e.data,
            "timestamp": e.created_at.isoformat() if e.created_at else None,
        }
        for e in events
    ]


def _generate_architecture_summary(
    mission: Mission, tasks: list[Task], agents: list[Agent]
) -> str:
    task_breakdown = "\n".join(
        f"- **{t.title}** ({t.assignee_role}): {t.description}" for t in tasks
    )
    agent_breakdown = "\n".join(
        f"- **{a.name}** ({a.role}) — Authority: {a.authority_level}, Model: {a.model}"
        for a in agents
    )

    return f"""# Architecture Summary — {mission.title}

## Goal
{mission.goal}

## Specification
{mission.specification or "N/A"}

## Agent Configuration
{agent_breakdown}

## Task Breakdown
{task_breakdown}

Generated at: {datetime.now(timezone.utc).isoformat()}
"""
