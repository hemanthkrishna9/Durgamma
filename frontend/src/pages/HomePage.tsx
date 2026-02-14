import { useNavigate } from "react-router-dom";
import { useMissions } from "../hooks/useMission";
import { Rocket, Clock, CheckCircle, AlertCircle, Play } from "lucide-react";

const statusColors: Record<string, string> = {
  intake: "#6b7280",
  clarifying: "#f59e0b",
  planning: "#3b82f6",
  approved: "#10b981",
  executing: "#8b5cf6",
  reviewing: "#f97316",
  deploying: "#06b6d4",
  delivered: "#22c55e",
  closed: "#6b7280",
  paused: "#ef4444",
  failed: "#dc2626",
};

export default function HomePage() {
  const { missions, loading, error, refresh } = useMissions();
  const navigate = useNavigate();

  if (loading) return <div className="page-loading">Loading missions...</div>;
  if (error) return <div className="page-error">Error: {error}</div>;

  const active = missions.filter((m) => !["closed", "delivered", "failed"].includes(m.status));
  const completed = missions.filter((m) => ["closed", "delivered"].includes(m.status));

  return (
    <div className="page">
      <div className="page-header">
        <h1>Mission Control</h1>
        <button className="btn btn-primary" onClick={() => navigate("/new")}>
          <Rocket size={16} /> New Mission
        </button>
      </div>

      {missions.length === 0 ? (
        <div className="empty-state">
          <Rocket size={48} />
          <h2>No missions yet</h2>
          <p>Create your first mission to deploy an AI agent squad.</p>
          <button className="btn btn-primary" onClick={() => navigate("/new")}>
            Create Mission
          </button>
        </div>
      ) : (
        <>
          {active.length > 0 && (
            <section>
              <h2><Play size={20} /> Active Missions ({active.length})</h2>
              <div className="mission-grid">
                {active.map((m) => (
                  <div
                    key={m.id}
                    className="mission-card"
                    onClick={() => navigate(`/mission/${m.id}`)}
                  >
                    <div className="mission-card-header">
                      <span className="status-badge" style={{ background: statusColors[m.status] }}>
                        {m.status}
                      </span>
                    </div>
                    <h3>{m.title}</h3>
                    <p>{m.goal}</p>
                    <div className="mission-card-footer">
                      <span><Clock size={14} /> {new Date(m.created_at).toLocaleDateString()}</span>
                      {m.budget_cap > 0 && (
                        <span>${m.cost_spent.toFixed(2)} / ${m.budget_cap.toFixed(2)}</span>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </section>
          )}

          {completed.length > 0 && (
            <section>
              <h2><CheckCircle size={20} /> Completed ({completed.length})</h2>
              <div className="mission-grid">
                {completed.map((m) => (
                  <div
                    key={m.id}
                    className="mission-card completed"
                    onClick={() => navigate(`/mission/${m.id}`)}
                  >
                    <h3>{m.title}</h3>
                    <span className="status-badge" style={{ background: statusColors[m.status] }}>
                      {m.status}
                    </span>
                  </div>
                ))}
              </div>
            </section>
          )}
        </>
      )}
    </div>
  );
}
