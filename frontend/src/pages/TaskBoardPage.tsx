import { useEffect, useState, useRef, useCallback } from "react";
import { tasks as taskApi } from "../services/api";
import type { Task, TaskStatus } from "../types";

const COLUMNS: { key: TaskStatus; label: string; color: string }[] = [
  { key: "backlog", label: "Backlog", color: "#6b7280" },
  { key: "todo", label: "To Do", color: "#3b82f6" },
  { key: "in_progress", label: "In Progress", color: "#8b5cf6" },
  { key: "review", label: "Review", color: "#f59e0b" },
  { key: "done", label: "Done", color: "#22c55e" },
];

const POLL_INTERVAL = 5000; // refresh every 5 seconds

export default function TaskBoardPage() {
  const [allTasks, setTasks] = useState<Task[]>([]);
  const [loading, setLoading] = useState(true);
  const [draggedTaskId, setDraggedTaskId] = useState<string | null>(null);
  const [dragOverCol, setDragOverCol] = useState<string | null>(null);
  const [updating, setUpdating] = useState<string | null>(null);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const fetchTasks = useCallback(() => {
    taskApi.list().then(setTasks).catch(() => {});
  }, []);

  // Initial load
  useEffect(() => {
    taskApi
      .list()
      .then(setTasks)
      .finally(() => setLoading(false));
  }, []);

  // Auto-refresh polling
  useEffect(() => {
    pollRef.current = setInterval(fetchTasks, POLL_INTERVAL);
    return () => {
      if (pollRef.current) clearInterval(pollRef.current);
    };
  }, [fetchTasks]);

  // --- Drag & Drop handlers ---
  const handleDragStart = (e: React.DragEvent, taskId: string) => {
    setDraggedTaskId(taskId);
    e.dataTransfer.effectAllowed = "move";
    e.dataTransfer.setData("text/plain", taskId);
    // Make the drag ghost slightly transparent
    if (e.currentTarget instanceof HTMLElement) {
      e.currentTarget.style.opacity = "0.5";
    }
  };

  const handleDragEnd = (e: React.DragEvent) => {
    setDraggedTaskId(null);
    setDragOverCol(null);
    if (e.currentTarget instanceof HTMLElement) {
      e.currentTarget.style.opacity = "1";
    }
  };

  const handleDragOver = (e: React.DragEvent, colKey: string) => {
    e.preventDefault();
    e.dataTransfer.dropEffect = "move";
    setDragOverCol(colKey);
  };

  const handleDragLeave = () => {
    setDragOverCol(null);
  };

  const handleDrop = async (e: React.DragEvent, targetStatus: TaskStatus) => {
    e.preventDefault();
    setDragOverCol(null);
    const taskId = e.dataTransfer.getData("text/plain");
    if (!taskId) return;

    const task = allTasks.find((t) => t.id === taskId);
    if (!task || task.status === targetStatus) return;

    // Optimistically update UI
    setTasks((prev) =>
      prev.map((t) => (t.id === taskId ? { ...t, status: targetStatus } : t))
    );
    setUpdating(taskId);

    try {
      const updated = await taskApi.update(taskId, { status: targetStatus });
      setTasks((prev) =>
        prev.map((t) => (t.id === taskId ? updated : t))
      );
    } catch {
      // Revert on failure
      setTasks((prev) =>
        prev.map((t) => (t.id === taskId ? { ...t, status: task.status } : t))
      );
    } finally {
      setUpdating(null);
    }
  };

  if (loading) return <div className="page-loading">Loading tasks...</div>;

  const grouped = COLUMNS.map((col) => ({
    ...col,
    tasks: allTasks
      .filter((t) => t.status === col.key)
      .sort((a, b) => b.priority - a.priority),
  }));

  return (
    <div className="page">
      <div className="page-header">
        <h1>Task Board</h1>
        <span className="muted">
          Agents auto-progress tasks | Live updates
        </span>
      </div>
      <div className="kanban-board">
        {grouped.map((col) => (
          <div
            key={col.key}
            className={`kanban-column${dragOverCol === col.key ? " kanban-column-dragover" : ""}`}
            onDragOver={(e) => handleDragOver(e, col.key)}
            onDragLeave={handleDragLeave}
            onDrop={(e) => handleDrop(e, col.key)}
          >
            <div className="kanban-header" style={{ borderColor: col.color }}>
              <span>{col.label}</span>
              <span className="kanban-count">{col.tasks.length}</span>
            </div>
            <div className="kanban-cards">
              {col.tasks.map((task) => (
                <div
                  key={task.id}
                  className={`kanban-card${draggedTaskId === task.id ? " kanban-card-dragging" : ""}${updating === task.id ? " kanban-card-updating" : ""}`}
                  draggable
                  onDragStart={(e) => handleDragStart(e, task.id)}
                  onDragEnd={handleDragEnd}
                >
                  <div className="kanban-card-title">{task.title}</div>
                  {task.assignee_role && (
                    <span className="kanban-card-assignee">{task.assignee_role}</span>
                  )}
                  {task.description && (
                    <p className="kanban-card-desc">
                      {task.description.slice(0, 100)}
                    </p>
                  )}
                  {task.dependencies.length > 0 && (
                    <div className="kanban-card-deps">
                      {task.dependencies.length} dep
                      {task.dependencies.length > 1 ? "s" : ""}
                    </div>
                  )}
                  {task.requires_approval && (
                    <span className="approval-badge">Needs Approval</span>
                  )}
                  {task.progress && (
                    <p className="kanban-card-progress">{task.progress}</p>
                  )}
                </div>
              ))}
              {col.tasks.length === 0 && (
                <div className="kanban-empty">
                  {dragOverCol === col.key ? "Drop here" : "No tasks"}
                </div>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
