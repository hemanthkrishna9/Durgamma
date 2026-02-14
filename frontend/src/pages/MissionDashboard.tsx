import { useParams, useNavigate } from "react-router-dom";
import { useMissionDetail } from "../hooks/useMission";
import { missions } from "../services/api";
import { Users, ListTodo, DollarSign, Activity, Pause, Play, XCircle } from "lucide-react";

export default function MissionDashboard() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { mission, tasks, agents, activityFeed, costSummary, loading, error, refresh } =
    useMissionDetail(id);

  if (loading) return <div className="page-loading">Loading mission...</div>;
  if (error || !mission) return <div className="page-error">{error || "Mission not found"}</div>;

  const doneTasks = tasks.filter((t) => t.status === "done").length;
  const totalTasks = tasks.length;
  const activeAgents = agents.filter((a) => ["active", "working"].includes(a.status)).length;

  const handlePause = async () => { await missions.pause(mission.id); refresh(); };
  const handleResume = async () => { await missions.resume(mission.id); refresh(); };
  const handleTerminate = async () => {
    if (confirm("Terminate this mission? All agents will be stopped.")) {
      await missions.terminate(mission.id);
      refresh();
    }
  };

  return (
    <div className="page">
      <div className="page-header">
        <div>
          <h1>{mission.title}</h1>
          <span className="status-badge" style={{ background: "#8b5cf6" }}>{mission.status}</span>
        </div>
        <div className="header-actions">
          {mission.status === "executing" && (
            <>
              <button className="btn btn-warning" onClick={handlePause}><Pause size={16} /> Pause</button>
              <button className="btn btn-danger" onClick={handleTerminate}><XCircle size={16} /> Terminate</button>
            </>
          )}
          {mission.status === "paused" && (
            <button className="btn btn-primary" onClick={handleResume}><Play size={16} /> Resume</button>
          )}
        </div>
      </div>

      <div className="stats-grid">
        <div className="stat-card" onClick={() => navigate("/tasks")}>
          <ListTodo size={24} />
          <div className="stat-value">{doneTasks}/{totalTasks}</div>
          <div className="stat-label">Tasks Complete</div>
        </div>
        <div className="stat-card" onClick={() => navigate("/agents")}>
          <Users size={24} />
          <div className="stat-value">{activeAgents}/{agents.length}</div>
          <div className="stat-label">Active Agents</div>
        </div>
        <div className="stat-card" onClick={() => navigate("/cost")}>
          <DollarSign size={24} />
          <div className="stat-value">${costSummary?.total_cost.toFixed(2) || "0.00"}</div>
          <div className="stat-label">Cost ({costSummary?.budget_percentage.toFixed(0) || 0}%)</div>
          {mission.budget_cap > 0 && (
            <div className="budget-bar">
              <div
                className="budget-fill"
                style={{ width: `${Math.min(costSummary?.budget_percentage || 0, 100)}%` }}
              />
            </div>
          )}
        </div>
        <div className="stat-card" onClick={() => navigate("/activity")}>
          <Activity size={24} />
          <div className="stat-value">{activityFeed.length}</div>
          <div className="stat-label">Activity Events</div>
        </div>
      </div>

      <div className="dashboard-grid">
        <section className="dashboard-section">
          <h2>Recent Activity</h2>
          <div className="activity-list">
            {activityFeed.slice(0, 10).map((entry) => (
              <div key={entry.id} className="activity-item">
                <span className="activity-time">
                  {new Date(entry.created_at).toLocaleTimeString()}
                </span>
                {entry.agent_name && <span className="activity-agent">[{entry.agent_name}]</span>}
                <span className="activity-content">{entry.content}</span>
              </div>
            ))}
            {activityFeed.length === 0 && <p className="muted">No activity yet.</p>}
          </div>
        </section>

        <section className="dashboard-section">
          <h2>Agent Status</h2>
          <div className="agent-list">
            {agents.map((agent) => (
              <div key={agent.id} className="agent-row">
                <span className={`agent-status-dot ${agent.status}`} />
                <strong>{agent.name}</strong>
                <span className="muted">{agent.role}</span>
                <span className="agent-status-text">{agent.status}</span>
              </div>
            ))}
          </div>
        </section>
      </div>
    </div>
  );
}
