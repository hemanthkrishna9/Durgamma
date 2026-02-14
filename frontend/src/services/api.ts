const BASE_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

async function request<T>(
  path: string,
  options: RequestInit = {}
): Promise<T> {
  const res = await fetch(`${BASE_URL}${path}`, {
    headers: { "Content-Type": "application/json", ...options.headers },
    ...options,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || res.statusText);
  }
  if (res.status === 204) return undefined as T;
  return res.json();
}

import type {
  Mission,
  MissionPlan,
  Task,
  Agent,
  Approval,
  ActivityEntry,
  CostSummary,
  EventRecord,
} from "../types";

// --- Missions ---
export const missions = {
  list: () => request<Mission[]>("/api/missions"),
  get: (id: string) => request<Mission>(`/api/missions/${id}`),
  create: (data: { title: string; goal: string; customer_name?: string; budget_cap?: number }) =>
    request<Mission>("/api/missions", { method: "POST", body: JSON.stringify(data) }),
  update: (id: string, data: Partial<Mission>) =>
    request<Mission>(`/api/missions/${id}`, { method: "PATCH", body: JSON.stringify(data) }),
  delete: (id: string) =>
    request<void>(`/api/missions/${id}`, { method: "DELETE" }),
  analyze: (id: string) =>
    request<MissionPlan>(`/api/missions/${id}/analyze`, { method: "POST" }),
  clarify: (id: string, answers: Record<string, string>) =>
    request<{ status: string }>(`/api/missions/${id}/clarify`, {
      method: "POST",
      body: JSON.stringify({ mission_id: id, answers }),
    }),
  approve: (id: string) =>
    request<{ status: string; agents_created: number; tasks_created: number }>(
      `/api/missions/${id}/approve`,
      { method: "POST" }
    ),
  terminate: (id: string) =>
    request<{ status: string }>(`/api/missions/${id}/terminate`, { method: "POST" }),
  pause: (id: string) =>
    request<{ status: string }>(`/api/missions/${id}/pause`, { method: "POST" }),
  resume: (id: string) =>
    request<{ status: string }>(`/api/missions/${id}/resume`, { method: "POST" }),
};

// --- Tasks ---
export const tasks = {
  list: (missionId?: string) => {
    const q = missionId ? `?mission_id=${missionId}` : "";
    return request<Task[]>(`/api/tasks${q}`);
  },
  get: (id: string) => request<Task>(`/api/tasks/${id}`),
  create: (data: {
    mission_id: string;
    title: string;
    description?: string;
    assignee_role?: string;
    dependencies?: string[];
  }) => request<Task>("/api/tasks", { method: "POST", body: JSON.stringify(data) }),
  update: (id: string, data: Partial<Task>) =>
    request<Task>(`/api/tasks/${id}`, { method: "PATCH", body: JSON.stringify(data) }),
  checkDeps: (id: string) => request<boolean>(`/api/tasks/${id}/dependencies-met`),
};

// --- Agents ---
export const agents = {
  list: (missionId?: string) => {
    const q = missionId ? `?mission_id=${missionId}` : "";
    return request<Agent[]>(`/api/agents${q}`);
  },
  get: (id: string) => request<Agent>(`/api/agents/${id}`),
};

// --- Approvals ---
export const approvals = {
  list: (missionId?: string, status?: string) => {
    const params = new URLSearchParams();
    if (missionId) params.set("mission_id", missionId);
    if (status) params.set("status", status);
    const q = params.toString() ? `?${params}` : "";
    return request<Approval[]>(`/api/approvals${q}`);
  },
  create: (data: {
    mission_id: string;
    gate_type: string;
    title: string;
    description?: string;
  }) => request<Approval>("/api/approvals", { method: "POST", body: JSON.stringify(data) }),
  decide: (id: string, status: "approved" | "rejected", comment?: string) =>
    request<Approval>(`/api/approvals/${id}/decide`, {
      method: "POST",
      body: JSON.stringify({ status, comment: comment || "" }),
    }),
};

// --- Activity & Events ---
export const activity = {
  feed: (missionId: string, limit = 50) =>
    request<ActivityEntry[]>(`/api/activity/${missionId}?limit=${limit}`),
  events: (missionId: string, limit = 100) =>
    request<EventRecord[]>(`/api/events/${missionId}?limit=${limit}`),
};

// --- Cost ---
export const cost = {
  summary: (missionId: string) => request<CostSummary>(`/api/cost/${missionId}/summary`),
};

// --- WebSocket ---
export function connectWebSocket(
  missionId: string,
  onMessage: (data: { type: string; data: unknown }) => void
): WebSocket {
  const wsUrl = BASE_URL.replace("http", "ws");
  const ws = new WebSocket(`${wsUrl}/ws/${missionId}`);

  ws.onmessage = (event) => {
    try {
      const msg = JSON.parse(event.data);
      onMessage(msg);
    } catch {
      // ignore parse errors
    }
  };

  // Ping to keep alive
  const interval = setInterval(() => {
    if (ws.readyState === WebSocket.OPEN) ws.send("ping");
  }, 30000);

  ws.onclose = () => clearInterval(interval);
  return ws;
}

// --- Health ---
export const health = () => request<{ status: string }>("/api/health");
