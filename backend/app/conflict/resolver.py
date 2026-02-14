"""Conflict Resolution System.

Implements the hierarchy + domain authority + escalation protocol:
1. Check if conflict falls in one agent's domain -> that agent wins
2. If not, higher authority agent wins
3. If same level, same domain -> escalate to Orchestrator
4. If unresolvable -> escalate to customer
"""

import logging
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Agent, EventType
from app.events.service import log_event, post_activity
from app.workspace.registry import registry

logger = logging.getLogger(__name__)

# Domain -> which role has final say
DOMAIN_OWNERS = {
    "architecture": "architect",
    "tech_stack": "architect",
    "api_design": "architect",
    "database": "architect",
    "quality": "qa",
    "testing": "qa",
    "code_review": "qa",
    "infrastructure": "devops",
    "deployment": "devops",
    "ci_cd": "devops",
    "process": "orchestrator",
    "priority": "orchestrator",
    "scheduling": "orchestrator",
    "frontend": "frontend-dev",
    "ui": "frontend-dev",
    "backend": "backend-dev",
    "server": "backend-dev",
    "mobile": "mobile-dev",
    "design": "designer",
    "ux": "designer",
    "seo": "seo",
    "content": "content-writer",
    "retention": "retention",
    "email": "email-marketing",
    "data_engineering": "data-engineer",
    "machine_learning": "ml-engineer",
    "analytics": "analytics",
    "research": "researcher",
    "support": "customer-support",
    "requirements": "customer",  # customer always wins on requirements
    "features": "customer",
}


class ConflictResolver:
    """Resolves conflicts between agents using hierarchy and domain authority."""

    async def resolve(
        self,
        db: AsyncSession,
        mission_id: str,
        agent_a_id: str,
        agent_b_id: str,
        domain: str,
        description: str,
    ) -> dict[str, Any]:
        """Resolve a conflict between two agents.

        Returns:
            {
                "resolution": "agent_a" | "agent_b" | "escalate_orchestrator" | "escalate_customer",
                "winner_id": str | None,
                "reason": str,
            }
        """
        agent_a = await db.get(Agent, agent_a_id)
        agent_b = await db.get(Agent, agent_b_id)

        if not agent_a or not agent_b:
            return {
                "resolution": "error",
                "winner_id": None,
                "reason": "One or both agents not found",
            }

        # Log the conflict
        await log_event(
            db, mission_id, EventType.CONFLICT_DETECTED,
            message=f"Conflict between {agent_a.name} ({agent_a.role}) and {agent_b.name} ({agent_b.role}): {description}",
            data={
                "agent_a": agent_a_id,
                "agent_b": agent_b_id,
                "domain": domain,
                "description": description,
            },
        )
        await post_activity(
            db, mission_id, "conflict",
            f"[CONFLICT] {agent_a.name} vs {agent_b.name}: {description}",
        )

        # Step 1: Check domain ownership
        domain_lower = domain.lower().replace(" ", "_")
        domain_owner_role = DOMAIN_OWNERS.get(domain_lower)

        if domain_owner_role == "customer":
            result = {
                "resolution": "escalate_customer",
                "winner_id": None,
                "reason": f"Domain '{domain}' requires customer decision",
            }
        elif domain_owner_role:
            if agent_a.role == domain_owner_role:
                result = {
                    "resolution": "agent_a",
                    "winner_id": agent_a_id,
                    "reason": f"{agent_a.name} owns the '{domain}' domain",
                }
            elif agent_b.role == domain_owner_role:
                result = {
                    "resolution": "agent_b",
                    "winner_id": agent_b_id,
                    "reason": f"{agent_b.name} owns the '{domain}' domain",
                }
            else:
                # Neither agent owns this domain — fall through to authority
                result = self._resolve_by_authority(agent_a, agent_b)
        else:
            # Unknown domain — resolve by authority
            result = self._resolve_by_authority(agent_a, agent_b)

        # Log the resolution
        await log_event(
            db, mission_id, EventType.CONFLICT_RESOLVED,
            message=f"Conflict resolved: {result['reason']}",
            data=result,
        )
        await post_activity(
            db, mission_id, "conflict_resolved",
            f"[RESOLVED] {result['reason']}",
        )

        await db.commit()
        return result

    def _resolve_by_authority(self, agent_a: Agent, agent_b: Agent) -> dict[str, Any]:
        """Resolve by comparing authority levels."""
        if agent_a.authority_level > agent_b.authority_level:
            return {
                "resolution": "agent_a",
                "winner_id": agent_a.id,
                "reason": f"{agent_a.name} has higher authority ({agent_a.authority_level} > {agent_b.authority_level})",
            }
        elif agent_b.authority_level > agent_a.authority_level:
            return {
                "resolution": "agent_b",
                "winner_id": agent_b.id,
                "reason": f"{agent_b.name} has higher authority ({agent_b.authority_level} > {agent_a.authority_level})",
            }
        else:
            # Same authority — escalate to orchestrator
            return {
                "resolution": "escalate_orchestrator",
                "winner_id": None,
                "reason": f"Equal authority ({agent_a.authority_level}). Escalated to Orchestrator.",
            }


class DivergenceDetector:
    """Detects when agents have diverged from the plan."""

    async def check_divergence(
        self, db: AsyncSession, mission_id: str
    ) -> list[dict[str, Any]]:
        """Check for divergences in the mission.

        Looks for:
        - Tasks that have been in_progress too long without updates
        - Agents working on tasks not assigned to them
        - Tasks being worked on out of dependency order
        """
        from app.db.models import Task, TaskStatus
        from app.tasks.dependencies import are_dependencies_met

        issues = []

        # Get all tasks
        result = await db.execute(
            select(Task).where(Task.mission_id == mission_id)
        )
        tasks = list(result.scalars().all())

        # Get all agents
        agent_result = await db.execute(
            select(Agent).where(Agent.mission_id == mission_id)
        )
        agents = list(agent_result.scalars().all())
        agent_map = {a.id: a for a in agents}

        for task in tasks:
            # Check: task in_progress but dependencies not met
            if task.status == TaskStatus.IN_PROGRESS:
                deps_met = await are_dependencies_met(db, task)
                if not deps_met:
                    issues.append({
                        "type": "dependency_violation",
                        "task_id": task.id,
                        "task_title": task.title,
                        "message": f"Task '{task.title}' is in progress but has unmet dependencies",
                    })

            # Check: assigned agent doesn't match the task's role
            if task.assignee_agent_id and task.assignee_role:
                agent = agent_map.get(task.assignee_agent_id)
                if agent and agent.role != task.assignee_role:
                    issues.append({
                        "type": "role_mismatch",
                        "task_id": task.id,
                        "task_title": task.title,
                        "agent_id": agent.id,
                        "message": f"Task '{task.title}' assigned to {agent.name} ({agent.role}) but expected {task.assignee_role}",
                    })

            # Check: too many retries
            if task.retry_count >= task.max_retries and task.status != TaskStatus.DONE:
                issues.append({
                    "type": "max_retries",
                    "task_id": task.id,
                    "task_title": task.title,
                    "message": f"Task '{task.title}' has reached max retries ({task.max_retries})",
                })

        return issues


# API Router for conflict resolution
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from app.db.database import get_db

router = APIRouter(prefix="/api/conflicts", tags=["conflicts"])

resolver = ConflictResolver()
detector = DivergenceDetector()


class ConflictRequest(BaseModel):
    mission_id: str
    agent_a_id: str
    agent_b_id: str
    domain: str
    description: str


@router.post("/resolve")
async def resolve_conflict(data: ConflictRequest, db: AsyncSession = Depends(get_db)):
    result = await resolver.resolve(
        db, data.mission_id, data.agent_a_id, data.agent_b_id,
        data.domain, data.description,
    )
    return result


@router.get("/{mission_id}/divergences")
async def check_divergences(mission_id: str, db: AsyncSession = Depends(get_db)):
    issues = await detector.check_divergence(db, mission_id)
    return {"mission_id": mission_id, "issues": issues, "count": len(issues)}
