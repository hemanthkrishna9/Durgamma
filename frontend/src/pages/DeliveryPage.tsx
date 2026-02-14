import { useEffect, useState } from "react";
import { missions as missionApi } from "../services/api";
import type { Mission } from "../types";
import { Package, Download, GitBranch, FileText } from "lucide-react";

export default function DeliveryPage() {
  const [allMissions, setMissions] = useState<Mission[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    missionApi.list().then(setMissions).finally(() => setLoading(false));
  }, []);

  const delivered = allMissions.filter((m) => ["delivered", "closed"].includes(m.status));
  const inProgress = allMissions.filter((m) => ["executing", "reviewing", "deploying"].includes(m.status));

  if (loading) return <div className="page-loading">Loading...</div>;

  return (
    <div className="page">
      <h1><Package size={24} /> Delivery & Handoff</h1>

      {allMissions.length === 0 ? (
        <div className="empty-state">
          <Package size={48} />
          <p>No missions yet. Completed missions will appear here for delivery.</p>
        </div>
      ) : (
        <>
          {inProgress.length > 0 && (
            <section>
              <h2>In Progress ({inProgress.length})</h2>
              {inProgress.map((m) => (
                <div key={m.id} className="delivery-card">
                  <h3>{m.title}</h3>
                  <span className="status-badge">{m.status}</span>
                  <p className="muted">Mission is still running. Delivery will be available after completion.</p>
                </div>
              ))}
            </section>
          )}

          {delivered.length > 0 && (
            <section>
              <h2>Ready for Delivery ({delivered.length})</h2>
              {delivered.map((m) => (
                <div key={m.id} className="delivery-card ready">
                  <h3>{m.title}</h3>
                  <p>Total cost: ${m.cost_spent.toFixed(2)}</p>
                  <div className="delivery-actions">
                    <button className="btn btn-primary">
                      <Download size={16} /> Download Package
                    </button>
                    <button className="btn btn-secondary">
                      <GitBranch size={16} /> View Repository
                    </button>
                    <button className="btn btn-secondary">
                      <FileText size={16} /> View Documentation
                    </button>
                  </div>
                </div>
              ))}
            </section>
          )}
        </>
      )}
    </div>
  );
}
