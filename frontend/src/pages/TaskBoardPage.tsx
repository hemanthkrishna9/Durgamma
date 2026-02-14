import { useEffect, useState } from "react";
import { tasks as taskApi } from "../services/api";
import type { Task, TaskStatus } from "../types";

const COLUMNS: { key: TaskStatus; label: string; color: string }[] = [
  { key: "backlog", label: "Backlog", color: "#6b7280" },
  { key: "todo", label: "To Do", color: "#3b82f6" },
  { key: "in_progress", label: "In Progress", color: "#8b5cf6" },
  { key: "review", label: "Review", color: "#f59e0b" },
  { key: "done", label: "Done", color: "#22c55e" },
];

export default function TaskBoardPage() {
  const [allTasks, setTasks] = useState<Task[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    taskApi.list().then(setTasks).finally(() => setLoading(false));
  }, []);

  if (loading) return <div className="page-loading">Loading tasks...</div>;

  const grouped = COLUMNS.map((col) => ({
    ...col,
    tasks: allTasks.filter((t) => t.status === col.key).sort((a, b) => b.priority - a.priority),
  }));

  return (
    <div className="page">
      <h1>Task Board</h1>
      <div className="kanban-board">
        {grouped.map((col) => (
          <div key={col.key} className="kanban-column">
            <div className="kanban-header" style={{ borderColor: col.color }}>
              <span>{col.label}</span>
              <span className="kanban-count">{col.tasks.length}</span>
            </div>
            <div className="kanban-cards">
              {col.tasks.map((task) => (
                <div key={task.id} className="kanban-card">
                  <div className="kanban-card-title">{task.title}</div>
                  {task.assignee_role && (
                    <span className="kanban-card-assignee">{task.assignee_role}</span>
                  )}
                  {task.description && (
                    <p className="kanban-card-desc">{task.description.slice(0, 100)}</p>
                  )}
                  {task.dependencies.length > 0 && (
                    <div className="kanban-card-deps">
                      {task.dependencies.length} dep{task.dependencies.length > 1 ? "s" : ""}
                    </div>
                  )}
                  {task.requires_approval && <span className="approval-badge">Needs Approval</span>}
                  {task.progress && <p className="kanban-card-progress">{task.progress}</p>}
                </div>
              ))}
              {col.tasks.length === 0 && <div className="kanban-empty">No tasks</div>}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
