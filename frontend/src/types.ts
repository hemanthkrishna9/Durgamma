export type MissionStatus =
  | "intake"
  | "clarifying"
  | "planning"
  | "approved"
  | "executing"
  | "reviewing"
  | "deploying"
  | "delivered"
  | "closed"
  | "paused"
  | "failed";

export type TaskStatus =
  | "backlog"
  | "todo"
  | "in_progress"
  | "review"
  | "done"
  | "failed"
  | "blocked";

export type AgentStatus =
  | "initializing"
  | "active"
  | "sleeping"
  | "working"
  | "error"
  | "terminated";

export type ApprovalStatus = "pending" | "approved" | "rejected";

export interface Mission {
  id: string;
  title: string;
  goal: string;
  specification: string;
  status: MissionStatus;
  customer_name: string;
  budget_cap: number;
  cost_spent: number;
  spawn_plan: Record<string, unknown>;
  created_at: string;
  updated_at: string;
}

export interface Task {
  id: string;
  mission_id: string;
  title: string;
  description: string;
  status: TaskStatus;
  assignee_role: string;
  assignee_agent_id: string | null;
  dependencies: string[];
  priority: number;
  retry_count: number;
  max_retries: number;
  requires_approval: boolean;
  progress: string;
  output: string;
  created_at: string;
  updated_at: string;
}

export interface Agent {
  id: string;
  mission_id: string;
  role: string;
  name: string;
  status: AgentStatus;
  authority_level: number;
  model: string;
  current_task_id: string | null;
  session_id: string | null;
  workspace_path: string;
  last_heartbeat: string | null;
  tokens_used: number;
  cost_total: number;
  config: Record<string, unknown>;
  created_at: string;
  updated_at: string;
}

export interface Approval {
  id: string;
  mission_id: string;
  task_id: string | null;
  gate_type: string;
  title: string;
  description: string;
  status: ApprovalStatus;
  requested_by: string;
  decided_at: string | null;
  decision_comment: string;
  created_at: string;
}

export interface ActivityEntry {
  id: number;
  mission_id: string;
  agent_id: string | null;
  agent_name: string;
  agent_role: string;
  entry_type: string;
  content: string;
  extra_data: Record<string, unknown>;
  created_at: string;
}

export interface CostSummary {
  mission_id: string;
  total_cost: number;
  budget_cap: number;
  budget_percentage: number;
  per_agent: Record<string, number>;
  per_model: Record<string, number>;
  record_count: number;
}

export interface MissionPlan {
  mission_id: string;
  agents: Array<{
    role: string;
    name: string;
    model: string;
    authority_level: number;
  }>;
  tasks: Array<{
    title: string;
    description: string;
    assignee_role: string;
    dependencies: string[];
    priority: number;
    requires_approval: boolean;
  }>;
  estimated_cost: {
    min: number;
    max: number;
    num_agents: number;
    estimated_heartbeats: number;
  };
  clarification_needed: boolean;
  questions: string[];
}

export interface EventRecord {
  id: number;
  mission_id: string;
  event_type: string;
  agent_id: string | null;
  task_id: string | null;
  data: Record<string, unknown>;
  message: string;
  created_at: string;
}
