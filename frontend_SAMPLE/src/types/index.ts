export interface Agent {
  agentId: string;
  runId: string;
  parentAgentId: string | null;
  task: string | null;
  status: string; // "running" | "completed" | "failed" | "max_turns"
  totalTurns: number;
  finalResponse: string | null;
  childCount: number;
  startedAt: string | null;
  finishedAt: string | null;
}

export interface PipelineStep {
  id: number;
  stepName: string;
  status: string;
  confidence: Record<string, unknown> | null;
  runtimeSeconds: number | null;
}

export interface Hypothesis {
  id: string;
  proteinName: string | null;
  ligandName: string | null;
  status: string;
  steps: PipelineStep[];
}

export interface VizArtifact {
  id: number;
  tool: string;
  artifactType: string;
  filePath: string;
  fileFormat: string | null;
  metadata: Record<string, unknown>;
}

export interface ToolInvocation {
  id: number;
  tool: string;
  subcommand: string | null;
  status: string;
  runtimeSeconds: number | null;
  inputs: Record<string, unknown>;
  summary: Record<string, unknown>;
}

export interface RunCreateResponse {
  runId: string;
  agentId: string;
}

export interface RunStatusResponse {
  runId: string;
  agentId: string;
  status: string;
  totalTurns: number;
  finalResponse: string | null;
  startedAt: string | null;
  finishedAt: string | null;
}

export interface Stats {
  agentCount: number;
  hypothesisCount: number;
  proteinCount: number;
  ligandCount: number;
}
