"""Database models for Mission Control."""

import enum
from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    JSON,
)
from sqlalchemy.orm import DeclarativeBase, relationship


class Base(DeclarativeBase):
    pass


# --- Enums ---


class MissionStatus(str, enum.Enum):
    INTAKE = "intake"
    CLARIFYING = "clarifying"
    PLANNING = "planning"
    APPROVED = "approved"
    EXECUTING = "executing"
    REVIEWING = "reviewing"
    DEPLOYING = "deploying"
    DELIVERED = "delivered"
    CLOSED = "closed"
    PAUSED = "paused"
    FAILED = "failed"


class TaskStatus(str, enum.Enum):
    BACKLOG = "backlog"
    TODO = "todo"
    IN_PROGRESS = "in_progress"
    REVIEW = "review"
    DONE = "done"
    FAILED = "failed"
    BLOCKED = "blocked"


class AgentStatus(str, enum.Enum):
    INITIALIZING = "initializing"
    ACTIVE = "active"
    SLEEPING = "sleeping"
    WORKING = "working"
    ERROR = "error"
    TERMINATED = "terminated"


class ApprovalStatus(str, enum.Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class EventType(str, enum.Enum):
    MISSION_CREATED = "mission_created"
    MISSION_STATUS_CHANGED = "mission_status_changed"
    TASK_CREATED = "task_created"
    TASK_STATUS_CHANGED = "task_status_changed"
    TASK_ASSIGNED = "task_assigned"
    AGENT_SPAWNED = "agent_spawned"
    AGENT_STATUS_CHANGED = "agent_status_changed"
    AGENT_HEARTBEAT = "agent_heartbeat"
    AGENT_MESSAGE = "agent_message"
    CONFLICT_DETECTED = "conflict_detected"
    CONFLICT_RESOLVED = "conflict_resolved"
    APPROVAL_REQUESTED = "approval_requested"
    APPROVAL_DECIDED = "approval_decided"
    COST_ALERT = "cost_alert"
    BUDGET_PAUSED = "budget_paused"
    HANDOFF = "handoff"
    ERROR = "error"


# --- Helper ---

def utcnow() -> datetime:
    return datetime.now(timezone.utc)


# --- Models ---


class Mission(Base):
    __tablename__ = "missions"

    id = Column(String, primary_key=True)
    title = Column(String, nullable=False)
    goal = Column(Text, nullable=False)
    specification = Column(Text, default="")
    status = Column(Enum(MissionStatus), default=MissionStatus.INTAKE, nullable=False)
    customer_name = Column(String, default="")
    budget_cap = Column(Float, default=0.0)
    cost_spent = Column(Float, default=0.0)
    spawn_plan = Column(JSON, default=dict)
    created_at = Column(DateTime, default=utcnow, nullable=False)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow, nullable=False)

    agents = relationship("Agent", back_populates="mission", cascade="all, delete-orphan")
    tasks = relationship("Task", back_populates="mission", cascade="all, delete-orphan")
    approvals = relationship("Approval", back_populates="mission", cascade="all, delete-orphan")
    events = relationship("Event", back_populates="mission", cascade="all, delete-orphan")
    cost_records = relationship("CostRecord", back_populates="mission", cascade="all, delete-orphan")


class Agent(Base):
    __tablename__ = "agents"

    id = Column(String, primary_key=True)
    mission_id = Column(String, ForeignKey("missions.id"), nullable=False)
    role = Column(String, nullable=False)
    name = Column(String, nullable=False)
    status = Column(Enum(AgentStatus), default=AgentStatus.INITIALIZING, nullable=False)
    authority_level = Column(Integer, default=50)
    model = Column(String, default="claude-sonnet-4-20250514")
    current_task_id = Column(String, ForeignKey("tasks.id"), nullable=True)
    session_id = Column(String, nullable=True)  # OpenClaw session ID
    workspace_path = Column(String, default="")
    last_heartbeat = Column(DateTime, nullable=True)
    tokens_used = Column(Integer, default=0)
    cost_total = Column(Float, default=0.0)
    config = Column(JSON, default=dict)
    created_at = Column(DateTime, default=utcnow, nullable=False)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow, nullable=False)

    mission = relationship("Mission", back_populates="agents")
    current_task = relationship("Task", foreign_keys=[current_task_id])


class Task(Base):
    __tablename__ = "tasks"

    id = Column(String, primary_key=True)
    mission_id = Column(String, ForeignKey("missions.id"), nullable=False)
    title = Column(String, nullable=False)
    description = Column(Text, default="")
    status = Column(Enum(TaskStatus), default=TaskStatus.BACKLOG, nullable=False)
    assignee_role = Column(String, default="")
    assignee_agent_id = Column(String, nullable=True)
    dependencies = Column(JSON, default=list)  # list of task IDs
    priority = Column(Integer, default=0)
    retry_count = Column(Integer, default=0)
    max_retries = Column(Integer, default=3)
    requires_approval = Column(Boolean, default=False)
    progress = Column(Text, default="")
    output = Column(Text, default="")
    created_at = Column(DateTime, default=utcnow, nullable=False)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow, nullable=False)

    mission = relationship("Mission", back_populates="tasks")


class TaskDependency(Base):
    __tablename__ = "task_dependencies"

    id = Column(Integer, primary_key=True, autoincrement=True)
    task_id = Column(String, ForeignKey("tasks.id"), nullable=False)
    depends_on_id = Column(String, ForeignKey("tasks.id"), nullable=False)


class Approval(Base):
    __tablename__ = "approvals"

    id = Column(String, primary_key=True)
    mission_id = Column(String, ForeignKey("missions.id"), nullable=False)
    task_id = Column(String, ForeignKey("tasks.id"), nullable=True)
    gate_type = Column(String, nullable=False)  # e.g. "deploy_staging", "deploy_prod", "mission_start"
    title = Column(String, nullable=False)
    description = Column(Text, default="")
    status = Column(Enum(ApprovalStatus), default=ApprovalStatus.PENDING, nullable=False)
    requested_by = Column(String, default="")  # agent role or "system"
    decided_at = Column(DateTime, nullable=True)
    decision_comment = Column(Text, default="")
    created_at = Column(DateTime, default=utcnow, nullable=False)

    mission = relationship("Mission", back_populates="approvals")


class Event(Base):
    __tablename__ = "events"

    id = Column(Integer, primary_key=True, autoincrement=True)
    mission_id = Column(String, ForeignKey("missions.id"), nullable=False)
    event_type = Column(Enum(EventType), nullable=False)
    agent_id = Column(String, nullable=True)
    task_id = Column(String, nullable=True)
    data = Column(JSON, default=dict)
    message = Column(Text, default="")
    created_at = Column(DateTime, default=utcnow, nullable=False)

    mission = relationship("Mission", back_populates="events")


class CostRecord(Base):
    __tablename__ = "cost_records"

    id = Column(Integer, primary_key=True, autoincrement=True)
    mission_id = Column(String, ForeignKey("missions.id"), nullable=False)
    agent_id = Column(String, ForeignKey("agents.id"), nullable=True)
    model = Column(String, nullable=False)
    input_tokens = Column(Integer, default=0)
    output_tokens = Column(Integer, default=0)
    cost = Column(Float, default=0.0)
    task_id = Column(String, nullable=True)
    created_at = Column(DateTime, default=utcnow, nullable=False)

    mission = relationship("Mission", back_populates="cost_records")


class ActivityEntry(Base):
    __tablename__ = "activity_feed"

    id = Column(Integer, primary_key=True, autoincrement=True)
    mission_id = Column(String, ForeignKey("missions.id"), nullable=False)
    agent_id = Column(String, nullable=True)
    agent_name = Column(String, default="")
    agent_role = Column(String, default="")
    entry_type = Column(String, nullable=False)  # status_change, progress, mention, handoff, conflict, escalation
    content = Column(Text, nullable=False)
    extra_data = Column(JSON, default=dict)
    created_at = Column(DateTime, default=utcnow, nullable=False)
