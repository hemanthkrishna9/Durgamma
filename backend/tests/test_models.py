"""Tests for database models and schema."""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.db.models import (
    Agent,
    AgentStatus,
    Approval,
    ApprovalStatus,
    Base,
    CostRecord,
    Event,
    EventType,
    Mission,
    MissionStatus,
    Task,
    TaskDependency,
    TaskStatus,
    ActivityEntry,
)
from app.schemas import (
    MissionCreate,
    MissionResponse,
    TaskCreate,
    TaskResponse,
    AgentResponse,
    CostSummary,
)


@pytest.fixture
async def db_engine():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest.fixture
async def db_session(db_engine):
    session_factory = async_sessionmaker(db_engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        yield session


async def test_create_mission(db_session: AsyncSession):
    mission = Mission(
        id="mission-001",
        title="Build a Todo App",
        goal="Build me a todo app with React and Python",
        status=MissionStatus.INTAKE,
        customer_name="Test Customer",
        budget_cap=50.0,
    )
    db_session.add(mission)
    await db_session.commit()

    result = await db_session.get(Mission, "mission-001")
    assert result is not None
    assert result.title == "Build a Todo App"
    assert result.status == MissionStatus.INTAKE
    assert result.budget_cap == 50.0
    assert result.cost_spent == 0.0


async def test_create_agent(db_session: AsyncSession):
    mission = Mission(
        id="mission-002",
        title="Test Mission",
        goal="Test goal",
    )
    db_session.add(mission)
    await db_session.commit()

    agent = Agent(
        id="agent-001",
        mission_id="mission-002",
        role="orchestrator",
        name="Orca",
        authority_level=100,
        model="claude-sonnet-4-20250514",
    )
    db_session.add(agent)
    await db_session.commit()

    result = await db_session.get(Agent, "agent-001")
    assert result is not None
    assert result.role == "orchestrator"
    assert result.authority_level == 100
    assert result.status == AgentStatus.INITIALIZING


async def test_create_task_with_dependencies(db_session: AsyncSession):
    mission = Mission(id="mission-003", title="Test", goal="Test")
    db_session.add(mission)
    await db_session.commit()

    task1 = Task(
        id="task-001",
        mission_id="mission-003",
        title="Design Architecture",
        assignee_role="architect",
        dependencies=[],
    )
    task2 = Task(
        id="task-002",
        mission_id="mission-003",
        title="Build Backend",
        assignee_role="backend-dev",
        dependencies=["task-001"],
    )
    db_session.add_all([task1, task2])
    await db_session.commit()

    dep = TaskDependency(task_id="task-002", depends_on_id="task-001")
    db_session.add(dep)
    await db_session.commit()

    result = await db_session.get(Task, "task-002")
    assert result is not None
    assert result.dependencies == ["task-001"]
    assert result.status == TaskStatus.BACKLOG


async def test_create_event(db_session: AsyncSession):
    mission = Mission(id="mission-004", title="Test", goal="Test")
    db_session.add(mission)
    await db_session.commit()

    event = Event(
        mission_id="mission-004",
        event_type=EventType.MISSION_CREATED,
        data={"title": "Test"},
        message="Mission created",
    )
    db_session.add(event)
    await db_session.commit()

    assert event.id is not None
    assert event.event_type == EventType.MISSION_CREATED


async def test_create_approval(db_session: AsyncSession):
    mission = Mission(id="mission-005", title="Test", goal="Test")
    db_session.add(mission)
    await db_session.commit()

    approval = Approval(
        id="approval-001",
        mission_id="mission-005",
        gate_type="deploy_staging",
        title="Deploy to Staging",
        requested_by="devops",
    )
    db_session.add(approval)
    await db_session.commit()

    result = await db_session.get(Approval, "approval-001")
    assert result is not None
    assert result.status == ApprovalStatus.PENDING


async def test_create_cost_record(db_session: AsyncSession):
    mission = Mission(id="mission-006", title="Test", goal="Test")
    db_session.add(mission)
    await db_session.commit()

    agent = Agent(
        id="agent-002",
        mission_id="mission-006",
        role="architect",
        name="Archie",
    )
    db_session.add(agent)
    await db_session.commit()

    cost = CostRecord(
        mission_id="mission-006",
        agent_id="agent-002",
        model="claude-sonnet-4-20250514",
        input_tokens=1000,
        output_tokens=500,
        cost=0.015,
    )
    db_session.add(cost)
    await db_session.commit()

    assert cost.id is not None
    assert cost.cost == 0.015


async def test_create_activity_entry(db_session: AsyncSession):
    mission = Mission(id="mission-007", title="Test", goal="Test")
    db_session.add(mission)
    await db_session.commit()

    entry = ActivityEntry(
        mission_id="mission-007",
        agent_id="agent-001",
        agent_name="Orca",
        agent_role="orchestrator",
        entry_type="status_change",
        content="Agent started working",
    )
    db_session.add(entry)
    await db_session.commit()

    assert entry.id is not None
    assert entry.entry_type == "status_change"


async def test_mission_schema_validation():
    create = MissionCreate(
        title="Build a SaaS",
        goal="Build me a SaaS app for project management",
        customer_name="John",
        budget_cap=100.0,
    )
    assert create.title == "Build a SaaS"

    with pytest.raises(Exception):
        MissionCreate(title="", goal="test")


async def test_cost_summary_schema():
    summary = CostSummary(
        mission_id="m1",
        total_cost=25.50,
        budget_cap=100.0,
        budget_percentage=25.5,
        per_agent={"agent-001": 15.0, "agent-002": 10.50},
        per_model={"claude-sonnet-4-20250514": 20.0, "claude-haiku-4-20250514": 5.50},
        record_count=42,
    )
    assert summary.budget_percentage == 25.5
    assert len(summary.per_agent) == 2


async def test_cascade_delete(db_session: AsyncSession):
    mission = Mission(id="mission-008", title="Test", goal="Test")
    db_session.add(mission)
    await db_session.commit()

    agent = Agent(id="agent-003", mission_id="mission-008", role="qa", name="Quinn")
    task = Task(id="task-003", mission_id="mission-008", title="Test task")
    event = Event(
        mission_id="mission-008",
        event_type=EventType.TASK_CREATED,
        message="Task created",
    )
    db_session.add_all([agent, task, event])
    await db_session.commit()

    await db_session.delete(mission)
    await db_session.commit()

    assert await db_session.get(Agent, "agent-003") is None
    assert await db_session.get(Task, "task-003") is None
