import { useEffect, useState } from "react";
import { activity, missions as missionApi } from "../services/api";
import type { ActivityEntry, Mission } from "../types";

export default function ActivityFeedPage() {
  const [entries, setEntries] = useState<ActivityEntry[]>([]);
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
    activity.feed(selectedMission, 100).then(setEntries).finally(() => setLoading(false));
  }, [selectedMission]);

  const typeColors: Record<string, string> = {
    system: "#6b7280",
    status_change: "#3b82f6",
    task_update: "#8b5cf6",
    progress: "#22c55e",
    approval_request: "#f59e0b",
    approval_decision: "#10b981",
    conflict: "#ef4444",
    escalation: "#dc2626",
    handoff: "#06b6d4",
  };

  return (
    <div className="page">
      <div className="page-header">
        <h1>Activity Feed</h1>
        <select value={selectedMission} onChange={(e) => setSelectedMission(e.target.value)}>
          {allMissions.map((m) => (
            <option key={m.id} value={m.id}>{m.title}</option>
          ))}
        </select>
      </div>

      {loading ? (
        <div className="page-loading">Loading activity...</div>
      ) : entries.length === 0 ? (
        <p className="muted">No activity yet for this mission.</p>
      ) : (
        <div className="activity-feed">
          {entries.map((entry) => (
            <div key={entry.id} className="activity-feed-item">
              <div className="activity-feed-time">
                {new Date(entry.created_at).toLocaleString()}
              </div>
              <div
                className="activity-feed-type"
                style={{ color: typeColors[entry.entry_type] || "#6b7280" }}
              >
                {entry.entry_type}
              </div>
              <div className="activity-feed-content">
                {entry.agent_name && (
                  <span className="activity-feed-agent">[{entry.agent_name}]</span>
                )}
                {entry.content}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
