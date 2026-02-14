import { useEffect, useState } from "react";
import { cost, missions as missionApi } from "../services/api";
import type { CostSummary, Mission } from "../types";
import { DollarSign, AlertTriangle } from "lucide-react";

export default function CostTrackerPage() {
  const [summary, setSummary] = useState<CostSummary | null>(null);
  const [allMissions, setMissions] = useState<Mission[]>([]);
  const [selectedMission, setSelectedMission] = useState<string>("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    missionApi.list().then((m) => {
      setMissions(m);
      if (m.length > 0 && !selectedMission) setSelectedMission(m[0].id);
    });
  }, []);

  useEffect(() => {
    if (!selectedMission) { setLoading(false); return; }
    setLoading(true);
    cost.summary(selectedMission).then(setSummary).catch(() => setSummary(null)).finally(() => setLoading(false));
  }, [selectedMission]);

  const budgetColor = !summary ? "#6b7280"
    : summary.budget_percentage > 80 ? "#ef4444"
    : summary.budget_percentage > 50 ? "#f59e0b"
    : "#22c55e";

  return (
    <div className="page">
      <div className="page-header">
        <h1><DollarSign size={24} /> Cost Tracker</h1>
        <select value={selectedMission} onChange={(e) => setSelectedMission(e.target.value)}>
          {allMissions.map((m) => (
            <option key={m.id} value={m.id}>{m.title}</option>
          ))}
        </select>
      </div>

      {loading ? (
        <div className="page-loading">Loading costs...</div>
      ) : !summary ? (
        <p className="muted">No cost data available.</p>
      ) : (
        <>
          <div className="stats-grid">
            <div className="stat-card">
              <DollarSign size={24} />
              <div className="stat-value">${summary.total_cost.toFixed(2)}</div>
              <div className="stat-label">Total Cost</div>
            </div>
            <div className="stat-card">
              <div className="stat-value" style={{ color: budgetColor }}>
                {summary.budget_percentage.toFixed(1)}%
              </div>
              <div className="stat-label">of ${summary.budget_cap.toFixed(2)} budget</div>
              <div className="budget-bar">
                <div className="budget-fill" style={{ width: `${Math.min(summary.budget_percentage, 100)}%`, background: budgetColor }} />
              </div>
            </div>
            <div className="stat-card">
              <div className="stat-value">{summary.record_count}</div>
              <div className="stat-label">API Calls</div>
            </div>
          </div>

          {summary.budget_percentage >= 80 && (
            <div className="warning-banner">
              <AlertTriangle size={20} /> Budget is at {summary.budget_percentage.toFixed(0)}%! Consider increasing the budget or pausing agents.
            </div>
          )}

          <div className="dashboard-grid">
            <section className="dashboard-section">
              <h2>Cost per Agent</h2>
              {Object.entries(summary.per_agent).length > 0 ? (
                <table className="cost-table">
                  <thead><tr><th>Agent</th><th>Cost</th></tr></thead>
                  <tbody>
                    {Object.entries(summary.per_agent).map(([id, c]) => (
                      <tr key={id}><td>{id}</td><td>${c.toFixed(4)}</td></tr>
                    ))}
                  </tbody>
                </table>
              ) : <p className="muted">No per-agent data yet.</p>}
            </section>

            <section className="dashboard-section">
              <h2>Cost per Model</h2>
              {Object.entries(summary.per_model).length > 0 ? (
                <table className="cost-table">
                  <thead><tr><th>Model</th><th>Cost</th></tr></thead>
                  <tbody>
                    {Object.entries(summary.per_model).map(([model, c]) => (
                      <tr key={model}><td>{model}</td><td>${c.toFixed(4)}</td></tr>
                    ))}
                  </tbody>
                </table>
              ) : <p className="muted">No per-model data yet.</p>}
            </section>
          </div>
        </>
      )}
    </div>
  );
}
