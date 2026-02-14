import { useEffect, useState } from "react";
import { approvals as approvalApi } from "../services/api";
import type { Approval } from "../types";
import { ShieldCheck, Check, X } from "lucide-react";

export default function ApprovalsPage() {
  const [allApprovals, setApprovals] = useState<Approval[]>([]);
  const [loading, setLoading] = useState(true);
  const [comment, setComment] = useState("");

  const refresh = () => {
    approvalApi.list().then(setApprovals).finally(() => setLoading(false));
  };

  useEffect(() => { refresh(); }, []);

  const handleDecide = async (id: string, decision: "approved" | "rejected") => {
    await approvalApi.decide(id, decision, comment);
    setComment("");
    refresh();
  };

  const pending = allApprovals.filter((a) => a.status === "pending");
  const decided = allApprovals.filter((a) => a.status !== "pending");

  if (loading) return <div className="page-loading">Loading approvals...</div>;

  return (
    <div className="page">
      <h1><ShieldCheck size={24} /> Approval Gates</h1>

      {pending.length > 0 && (
        <section>
          <h2>Pending Approvals ({pending.length})</h2>
          {pending.map((a) => (
            <div key={a.id} className="approval-card pending">
              <div className="approval-header">
                <h3>{a.title}</h3>
                <span className="approval-type">{a.gate_type}</span>
              </div>
              <p>{a.description}</p>
              <p className="muted">Requested by: {a.requested_by}</p>
              <div className="approval-actions">
                <input placeholder="Comment (optional)" value={comment} onChange={(e) => setComment(e.target.value)} />
                <button className="btn btn-primary" onClick={() => handleDecide(a.id, "approved")}>
                  <Check size={16} /> Approve
                </button>
                <button className="btn btn-danger" onClick={() => handleDecide(a.id, "rejected")}>
                  <X size={16} /> Reject
                </button>
              </div>
            </div>
          ))}
        </section>
      )}

      {pending.length === 0 && (
        <div className="empty-state">
          <ShieldCheck size={48} />
          <p>No pending approvals.</p>
        </div>
      )}

      {decided.length > 0 && (
        <section>
          <h2>History ({decided.length})</h2>
          {decided.map((a) => (
            <div key={a.id} className={`approval-card ${a.status}`}>
              <div className="approval-header">
                <h3>{a.title}</h3>
                <span className={`status-badge ${a.status}`}>{a.status}</span>
              </div>
              {a.decision_comment && <p>Comment: {a.decision_comment}</p>}
              <p className="muted">{a.decided_at ? new Date(a.decided_at).toLocaleString() : ""}</p>
            </div>
          ))}
        </section>
      )}
    </div>
  );
}
