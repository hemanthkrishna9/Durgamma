import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { missions } from "../services/api";
import type { MissionPlan } from "../types";

export default function MissionIntakePage() {
  const navigate = useNavigate();
  const [step, setStep] = useState<"input" | "clarify" | "review">("input");
  const [title, setTitle] = useState("");
  const [goal, setGoal] = useState("");
  const [name, setName] = useState("");
  const [budget, setBudget] = useState(100);
  const [missionId, setMissionId] = useState("");
  const [plan, setPlan] = useState<MissionPlan | null>(null);
  const [answers, setAnswers] = useState<Record<string, string>>({});
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const handleSubmit = async () => {
    if (!title || !goal) return;
    setLoading(true);
    setError("");
    try {
      const mission = await missions.create({ title, goal, customer_name: name, budget_cap: budget });
      setMissionId(mission.id);
      const result = await missions.analyze(mission.id);
      setPlan(result);
      if (result.clarification_needed) {
        setStep("clarify");
      } else {
        setStep("review");
      }
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setLoading(false);
    }
  };

  const handleClarify = async () => {
    setLoading(true);
    try {
      await missions.clarify(missionId, answers);
      await missions.update(missionId, { specification: Object.values(answers).join(". ") } as never);
      const result = await missions.analyze(missionId);
      setPlan(result);
      setStep("review");
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setLoading(false);
    }
  };

  const handleApprove = async () => {
    setLoading(true);
    try {
      await missions.update(missionId, { budget_cap: budget } as never);
      await missions.approve(missionId);
      navigate(`/mission/${missionId}`);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="page">
      <h1>New Mission</h1>

      {error && <div className="error-banner">{error}</div>}

      {step === "input" && (
        <div className="form-card">
          <div className="form-group">
            <label>Mission Title</label>
            <input value={title} onChange={(e) => setTitle(e.target.value)} placeholder="e.g. Build a Food Delivery App" />
          </div>
          <div className="form-group">
            <label>Your Goal</label>
            <textarea value={goal} onChange={(e) => setGoal(e.target.value)} rows={4} placeholder="Describe what you want to achieve..." />
          </div>
          <div className="form-row">
            <div className="form-group">
              <label>Your Name</label>
              <input value={name} onChange={(e) => setName(e.target.value)} placeholder="Optional" />
            </div>
            <div className="form-group">
              <label>Budget Cap ($)</label>
              <input type="number" value={budget} onChange={(e) => setBudget(Number(e.target.value))} min={0} />
            </div>
          </div>
          <button className="btn btn-primary" onClick={handleSubmit} disabled={loading || !title || !goal}>
            {loading ? "Analyzing..." : "Analyze Mission"}
          </button>
        </div>
      )}

      {step === "clarify" && plan && (
        <div className="form-card">
          <h2>We need a few clarifications</h2>
          <p>Please answer these questions to help us plan your mission better:</p>
          {plan.questions.map((q, i) => (
            <div key={i} className="form-group">
              <label>{q}</label>
              <input value={answers[q] || ""} onChange={(e) => setAnswers({ ...answers, [q]: e.target.value })} />
            </div>
          ))}
          <button className="btn btn-primary" onClick={handleClarify} disabled={loading}>
            {loading ? "Re-analyzing..." : "Submit Answers"}
          </button>
        </div>
      )}

      {step === "review" && plan && (
        <div className="form-card">
          <h2>Mission Plan</h2>

          <div className="plan-section">
            <h3>Agent Squad ({plan.agents.length} agents)</h3>
            <div className="agent-chips">
              {plan.agents.map((a, i) => (
                <span key={i} className="agent-chip">{a.name} ({a.role})</span>
              ))}
            </div>
          </div>

          <div className="plan-section">
            <h3>Task Breakdown ({plan.tasks.length} tasks)</h3>
            <div className="task-list-preview">
              {plan.tasks.map((t, i) => (
                <div key={i} className="task-preview">
                  <strong>{t.title}</strong>
                  <span className="task-assignee">{t.assignee_role}</span>
                  {t.dependencies.length > 0 && (
                    <span className="task-deps">depends on: {t.dependencies.join(", ")}</span>
                  )}
                </div>
              ))}
            </div>
          </div>

          <div className="plan-section">
            <h3>Cost Estimate</h3>
            <p>${plan.estimated_cost.min.toFixed(2)} - ${plan.estimated_cost.max.toFixed(2)}</p>
            <p>{plan.estimated_cost.num_agents} agents, ~{plan.estimated_cost.estimated_heartbeats} heartbeat cycles</p>
          </div>

          <div className="form-group">
            <label>Budget Cap ($)</label>
            <input type="number" value={budget} onChange={(e) => setBudget(Number(e.target.value))} min={0} />
          </div>

          <div className="form-actions">
            <button className="btn btn-secondary" onClick={() => setStep("input")}>Back</button>
            <button className="btn btn-primary" onClick={handleApprove} disabled={loading}>
              {loading ? "Launching..." : "Approve & Launch Agents"}
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
