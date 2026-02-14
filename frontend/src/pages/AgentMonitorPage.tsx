import { useEffect, useState } from "react";
import { agents as agentApi } from "../services/api";
import type { Agent } from "../types";
import { Bot, Zap, Moon, AlertTriangle, XCircle } from "lucide-react";

const statusIcons: Record<string, React.ReactNode> = {
  active: <Zap size={16} color="#22c55e" />,
  working: <Zap size={16} color="#8b5cf6" />,
  sleeping: <Moon size={16} color="#6b7280" />,
  error: <AlertTriangle size={16} color="#ef4444" />,
  terminated: <XCircle size={16} color="#6b7280" />,
  initializing: <Bot size={16} color="#3b82f6" />,
};

export default function AgentMonitorPage() {
  const [allAgents, setAgents] = useState<Agent[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    agentApi.list().then(setAgents).finally(() => setLoading(false));
  }, []);

  if (loading) return <div className="page-loading">Loading agents...</div>;

  return (
    <div className="page">
      <h1>Agent Monitor</h1>
      {allAgents.length === 0 ? (
        <div className="empty-state">
          <Bot size={48} />
          <p>No agents spawned yet. Start a mission to see agents here.</p>
        </div>
      ) : (
        <div className="agent-cards-grid">
          {allAgents.map((agent) => (
            <div key={agent.id} className={`agent-card ${agent.status}`}>
              <div className="agent-card-header">
                {statusIcons[agent.status] || <Bot size={16} />}
                <h3>{agent.name}</h3>
                <span className="agent-role-badge">{agent.role}</span>
              </div>
              <div className="agent-card-body">
                <div className="agent-detail">
                  <span className="label">Status</span>
                  <span className={`status-text ${agent.status}`}>{agent.status}</span>
                </div>
                <div className="agent-detail">
                  <span className="label">Authority</span>
                  <span>{agent.authority_level}</span>
                </div>
                <div className="agent-detail">
                  <span className="label">Model</span>
                  <span>{agent.model.split("-").slice(0, 2).join("-")}</span>
                </div>
                <div className="agent-detail">
                  <span className="label">Tokens</span>
                  <span>{agent.tokens_used.toLocaleString()}</span>
                </div>
                <div className="agent-detail">
                  <span className="label">Cost</span>
                  <span>${agent.cost_total.toFixed(4)}</span>
                </div>
                {agent.last_heartbeat && (
                  <div className="agent-detail">
                    <span className="label">Last Heartbeat</span>
                    <span>{new Date(agent.last_heartbeat).toLocaleTimeString()}</span>
                  </div>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
