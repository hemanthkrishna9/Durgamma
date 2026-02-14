"""Pydantic schemas for API request/response models."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from app.db.models import (
    AgentStatus,
    ApprovalStatus,
    MissionStatus,
    TaskStatus,
)


# --- Mission ---


class MissionCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    goal: str = Field(..., min_length=1)
    customer_name: str = ""
    budget_cap: float = 0.0


class MissionUpdate(BaseModel):
    title: str | None = None
    goal: str | None = None
    specification: str | None = None
    status: MissionStatus | None = None
    budget_cap: float | None = None


class MissionResponse(BaseModel):
    id: str
    title: str
    goal: str
    specification: str
    status: MissionStatus
    customer_name: str
    budget_cap: float
    cost_spent: float
    spawn_plan: dict[str, Any]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class MissionClarification(BaseModel):
    mission_id: str
    answers: dict[str, str]


class MissionPlanResponse(BaseModel):
    mission_id: str
    agents: list[dict[str, Any]]
    tasks: list[dict[str, Any]]
    estimated_cost: dict[str, Any]
    clarification_needed: bool = False
    questions: list[str] = []


# --- Task ---


class TaskCreate(BaseModel):
    mission_id: str
    title: str = Field(..., min_length=1)
    description: str = ""
    assignee_role: str = ""
    dependencies: list[str] = []
    priority: int = 0
    requires_approval: bool = False


class TaskUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    status: TaskStatus | None = None
    assignee_role: str | None = None
    assignee_agent_id: str | None = None
    progress: str | None = None
    output: str | None = None


class TaskResponse(BaseModel):
    id: str
    mission_id: str
    title: str
    description: str
    status: TaskStatus
    assignee_role: str
    assignee_agent_id: str | None
    dependencies: list[str]
    priority: int
    retry_count: int
    max_retries: int
    requires_approval: bool
    progress: str
    output: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# --- Agent ---


class AgentCreate(BaseModel):
    mission_id: str
    role: str
    name: str
    authority_level: int = 50
    model: str = "claude-sonnet-4-20250514"
    config: dict[str, Any] = {}


class AgentResponse(BaseModel):
    id: str
    mission_id: str
    role: str
    name: str
    status: AgentStatus
    authority_level: int
    model: str
    current_task_id: str | None
    session_id: str | None
    workspace_path: str
    last_heartbeat: datetime | None
    tokens_used: int
    cost_total: float
    config: dict[str, Any]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# --- Approval ---


class ApprovalCreate(BaseModel):
    mission_id: str
    task_id: str | None = None
    gate_type: str
    title: str
    description: str = ""
    requested_by: str = "system"


class ApprovalDecision(BaseModel):
    status: ApprovalStatus
    comment: str = ""


class ApprovalResponse(BaseModel):
    id: str
    mission_id: str
    task_id: str | None
    gate_type: str
    title: str
    description: str
    status: ApprovalStatus
    requested_by: str
    decided_at: datetime | None
    decision_comment: str
    created_at: datetime

    model_config = {"from_attributes": True}


# --- Event ---


class EventResponse(BaseModel):
    id: int
    mission_id: str
    event_type: str
    agent_id: str | None
    task_id: str | None
    data: dict[str, Any]
    message: str
    created_at: datetime

    model_config = {"from_attributes": True}


# --- Activity Feed ---


class ActivityEntryResponse(BaseModel):
    id: int
    mission_id: str
    agent_id: str | None
    agent_name: str
    agent_role: str
    entry_type: str
    content: str
    extra_data: dict[str, Any]
    created_at: datetime

    model_config = {"from_attributes": True}


# --- Cost ---


class CostSummary(BaseModel):
    mission_id: str
    total_cost: float
    budget_cap: float
    budget_percentage: float
    per_agent: dict[str, float]
    per_model: dict[str, float]
    record_count: int


class CostRecordResponse(BaseModel):
    id: int
    mission_id: str
    agent_id: str | None
    model: str
    input_tokens: int
    output_tokens: int
    cost: float
    task_id: str | None
    created_at: datetime

    model_config = {"from_attributes": True}
