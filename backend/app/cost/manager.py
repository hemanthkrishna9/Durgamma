"""Budget Manager — tracks costs and enforces budget limits.

Alerts at thresholds:
- 50% budget -> dashboard notification
- 80% budget -> warning
- 100% budget -> ALL AGENTS PAUSED
"""

import logging
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Agent, CostRecord, EventType, Mission, MissionStatus
from app.events.service import log_event, post_activity
from app.websocket import ws_manager

logger = logging.getLogger(__name__)

# Model pricing (per 1M tokens) — approximate
MODEL_PRICING = {
    "claude-opus-4-20250514": {"input": 15.0, "output": 75.0},
    "claude-sonnet-4-20250514": {"input": 3.0, "output": 15.0},
    "claude-haiku-4-20250514": {"input": 0.80, "output": 4.0},
}

DEFAULT_PRICING = {"input": 3.0, "output": 15.0}


def estimate_cost(model: str, input_tokens: int, output_tokens: int) -> float:
    """Estimate cost for an API call based on model and token counts."""
    pricing = MODEL_PRICING.get(model, DEFAULT_PRICING)
    input_cost = (input_tokens / 1_000_000) * pricing["input"]
    output_cost = (output_tokens / 1_000_000) * pricing["output"]
    return round(input_cost + output_cost, 6)


async def record_cost(
    db: AsyncSession,
    mission_id: str,
    agent_id: str | None,
    model: str,
    input_tokens: int,
    output_tokens: int,
    task_id: str | None = None,
) -> dict[str, Any]:
    """Record an API call cost and check budget thresholds.

    Returns alert info if a threshold was crossed.
    """
    cost_amount = estimate_cost(model, input_tokens, output_tokens)

    record = CostRecord(
        mission_id=mission_id,
        agent_id=agent_id,
        model=model,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        cost=cost_amount,
        task_id=task_id,
    )
    db.add(record)

    # Update agent totals
    if agent_id:
        agent = await db.get(Agent, agent_id)
        if agent:
            agent.tokens_used += input_tokens + output_tokens
            agent.cost_total += cost_amount

    # Update mission total
    mission = await db.get(Mission, mission_id)
    if not mission:
        await db.flush()
        return {"cost": cost_amount, "alert": None}

    mission.cost_spent += cost_amount
    await db.flush()

    # Check thresholds
    alert = await _check_budget_thresholds(db, mission)

    return {"cost": cost_amount, "total": mission.cost_spent, "alert": alert}


async def _check_budget_thresholds(
    db: AsyncSession, mission: Mission
) -> dict[str, Any] | None:
    """Check if any budget thresholds have been crossed."""
    if mission.budget_cap <= 0:
        return None

    percentage = (mission.cost_spent / mission.budget_cap) * 100

    if percentage >= 100:
        # AUTO-PAUSE: Budget exceeded
        await log_event(
            db, mission.id, EventType.BUDGET_PAUSED,
            message=f"Budget exceeded! ${mission.cost_spent:.2f} / ${mission.budget_cap:.2f} ({percentage:.0f}%)",
            data={"spent": mission.cost_spent, "cap": mission.budget_cap, "percentage": percentage},
        )
        await post_activity(
            db, mission.id, "budget_alert",
            f"[BUDGET EXCEEDED] All agents paused. ${mission.cost_spent:.2f} / ${mission.budget_cap:.2f}",
        )

        # Pause the mission
        mission.status = MissionStatus.PAUSED

        # Pause all agents via orchestrator
        from app.mission.orchestrator import pause_all_agents
        await pause_all_agents(db, mission.id)

        # Broadcast to dashboard
        await ws_manager.broadcast(mission.id, "budget_exceeded", {
            "spent": mission.cost_spent,
            "cap": mission.budget_cap,
            "percentage": percentage,
        })

        return {"level": "critical", "message": "Budget exceeded. All agents paused.", "percentage": percentage}

    elif percentage >= 80:
        await log_event(
            db, mission.id, EventType.COST_ALERT,
            message=f"Budget warning: ${mission.cost_spent:.2f} / ${mission.budget_cap:.2f} ({percentage:.0f}%)",
            data={"level": "warning", "percentage": percentage},
        )
        await post_activity(
            db, mission.id, "budget_alert",
            f"[BUDGET WARNING] 80% budget used. ${mission.cost_spent:.2f} / ${mission.budget_cap:.2f}",
        )
        await ws_manager.broadcast(mission.id, "budget_warning", {
            "spent": mission.cost_spent, "cap": mission.budget_cap, "percentage": percentage,
        })
        return {"level": "warning", "message": "80% of budget used", "percentage": percentage}

    elif percentage >= 50:
        await log_event(
            db, mission.id, EventType.COST_ALERT,
            message=f"Budget notice: ${mission.cost_spent:.2f} / ${mission.budget_cap:.2f} ({percentage:.0f}%)",
            data={"level": "notice", "percentage": percentage},
        )
        await ws_manager.broadcast(mission.id, "budget_notice", {
            "spent": mission.cost_spent, "cap": mission.budget_cap, "percentage": percentage,
        })
        return {"level": "notice", "message": "50% of budget used", "percentage": percentage}

    return None


async def get_budget_status(db: AsyncSession, mission_id: str) -> dict[str, Any]:
    """Get current budget status for a mission."""
    mission = await db.get(Mission, mission_id)
    if not mission:
        return {"error": "Mission not found"}

    total_result = await db.execute(
        select(func.coalesce(func.sum(CostRecord.cost), 0.0))
        .where(CostRecord.mission_id == mission_id)
    )
    total_cost = float(total_result.scalar())

    percentage = (total_cost / mission.budget_cap * 100) if mission.budget_cap > 0 else 0

    return {
        "mission_id": mission_id,
        "total_cost": total_cost,
        "budget_cap": mission.budget_cap,
        "percentage": round(percentage, 2),
        "remaining": max(0, mission.budget_cap - total_cost),
        "status": (
            "exceeded" if percentage >= 100
            else "warning" if percentage >= 80
            else "notice" if percentage >= 50
            else "ok"
        ),
    }
