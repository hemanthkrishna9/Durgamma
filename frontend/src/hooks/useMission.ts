import { useCallback, useEffect, useState } from "react";
import { missions as missionApi, tasks as taskApi, agents as agentApi, activity, cost } from "../services/api";
import type { Mission, Task, Agent, ActivityEntry, CostSummary, MissionPlan } from "../types";

export function useMissions() {
  const [data, setData] = useState<Mission[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    setLoading(true);
    try {
      setData(await missionApi.list());
      setError(null);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { refresh(); }, [refresh]);
  return { missions: data, loading, error, refresh };
}

export function useMissionDetail(missionId: string | undefined) {
  const [mission, setMission] = useState<Mission | null>(null);
  const [missionTasks, setTasks] = useState<Task[]>([]);
  const [missionAgents, setAgents] = useState<Agent[]>([]);
  const [activityFeed, setActivity] = useState<ActivityEntry[]>([]);
  const [costSummary, setCost] = useState<CostSummary | null>(null);
  const [plan, setPlan] = useState<MissionPlan | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    if (!missionId) return;
    setLoading(true);
    try {
      const [m, t, a, act, c] = await Promise.all([
        missionApi.get(missionId),
        taskApi.list(missionId),
        agentApi.list(missionId),
        activity.feed(missionId),
        cost.summary(missionId).catch(() => null),
      ]);
      setMission(m);
      setTasks(t);
      setAgents(a);
      setActivity(act);
      setCost(c);
      setError(null);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setLoading(false);
    }
  }, [missionId]);

  useEffect(() => { refresh(); }, [refresh]);

  return { mission, tasks: missionTasks, agents: missionAgents, activityFeed, costSummary, plan, setPlan, loading, error, refresh };
}
