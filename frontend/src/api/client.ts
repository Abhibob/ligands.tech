const BASE = import.meta.env.VITE_API_URL || "";

async function get<T>(path: string): Promise<T> {
  const res = await fetch(`${BASE}${path}`);
  if (!res.ok) throw new Error(`API ${res.status}: ${path}`);
  return res.json();
}

async function post<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(`API ${res.status}: ${path}`);
  return res.json();
}

import type {
  Agent,
  Hypothesis,
  VizArtifact,
  ToolInvocation,
  RunCreateResponse,
  RunStatusResponse,
  Stats,
} from "../types";

export const api = {
  listAgents: (limit = 50, offset = 0, status?: string) => {
    const params = new URLSearchParams({ limit: String(limit), offset: String(offset) });
    if (status) params.set("status", status);
    return get<Agent[]>(`/api/agents?${params}`);
  },
  getAgent: (id: string) => get<Agent>(`/api/agents/${id}`),
  getAgentChildren: (id: string) => get<Agent[]>(`/api/agents/${id}/children`),
  getAgentHypotheses: (id: string) =>
    get<Hypothesis[]>(`/api/agents/${id}/hypotheses`),
  getAgentArtifacts: (id: string) =>
    get<VizArtifact[]>(`/api/agents/${id}/artifacts`),
  getAgentInvocations: (id: string) =>
    get<ToolInvocation[]>(`/api/agents/${id}/invocations`),
  getHypothesis: (id: string) => get<Hypothesis>(`/api/hypotheses/${id}`),
  getStats: () => get<Stats>("/api/stats"),
  createRun: (prompt: string) =>
    post<RunCreateResponse>("/api/runs", { prompt }),
  getRunStatus: (runId: string) =>
    get<RunStatusResponse>(`/api/runs/${runId}`),
  artifactUrl: (path: string) => `${BASE}/api/artifacts/${path}`,
};
