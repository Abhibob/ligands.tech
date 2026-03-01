import { useState, useEffect, useCallback } from "react";
import { useParams, useNavigate, Link } from "react-router-dom";
import { motion } from "framer-motion";
import { Archive, Brain } from "lucide-react";
import AgentSidebar from "../components/agents/AgentSidebar";
import HypothesisCardGrid from "../components/agents/HypothesisCardGrid";
import ThinkingSidebar from "../components/agents/ThinkingSidebar";
import { useAgentEvents } from "../hooks/useAgentEvents";
import { api } from "../api/client";
import type { Agent, Hypothesis } from "../types";

export default function AgentsPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();

  const [agents, setAgents] = useState<Agent[]>([]);
  const [hypotheses, setHypotheses] = useState<Hypothesis[]>([]);
  const [loading, setLoading] = useState(true);
  const [thinkingOpen, setThinkingOpen] = useState(false);

  const activeId = id || agents[0]?.agentId || null;
  const activeAgent = agents.find((a) => a.agentId === activeId) || null;

  // WebSocket events for the active agent
  const { events, connected } = useAgentEvents(activeId);

  // Load only running agents
  useEffect(() => {
    let cancelled = false;
    const load = async () => {
      try {
        const data = await api.listAgents(50, 0, "running");
        if (!cancelled) {
          setAgents(data);
          setLoading(false);
        }
      } catch {
        if (!cancelled) setLoading(false);
      }
    };
    load();
    // Poll every 3s for running agents
    const interval = setInterval(load, 3000);
    return () => {
      cancelled = true;
      clearInterval(interval);
    };
  }, []);

  // Load hypotheses for active agent
  const loadHypotheses = useCallback(async () => {
    if (!activeId) {
      setHypotheses([]);
      return;
    }
    try {
      const data = await api.getAgentHypotheses(activeId);
      setHypotheses(data);
    } catch {
      setHypotheses([]);
    }
  }, [activeId]);

  useEffect(() => {
    loadHypotheses();
    // Poll every 3s if the active agent is still running
    if (activeAgent?.status === "running") {
      const interval = setInterval(loadHypotheses, 3000);
      return () => clearInterval(interval);
    }
  }, [loadHypotheses, activeAgent?.status]);

  const handleChange = (agentId: string) => {
    navigate(`/agents/${agentId}`);
  };

  return (
    <div className="max-w-7xl mx-auto px-6 py-10">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-3xl font-bold text-slate-900">Running Agents</h1>
        <div className="flex items-center gap-3">
          {activeAgent?.status === "running" && (
            <button
              onClick={() => setThinkingOpen(true)}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 text-sm font-medium rounded-lg bg-slate-900 text-white hover:bg-slate-800 transition-colors"
            >
              <Brain className="w-4 h-4" />
              Show Thinking
              {connected && (
                <span className="relative flex h-2 w-2 ml-0.5">
                  <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-green-400 opacity-75" />
                  <span className="relative inline-flex rounded-full h-2 w-2 bg-green-500" />
                </span>
              )}
            </button>
          )}
          <Link
            to="/finished"
            className="inline-flex items-center gap-1.5 text-sm text-slate-500 hover:text-teal-600 transition-colors"
          >
            <Archive className="w-4 h-4" />
            Finished Agents
          </Link>
        </div>
      </div>
      <div className="flex gap-6 min-h-[calc(100vh-12rem)]">
        <AgentSidebar
          agents={agents}
          activeId={activeId}
          onChange={handleChange}
          loading={loading}
          emptyText="No running agents"
        />

        <div className="flex-1 min-w-0">
          {activeAgent && (
            <motion.div
              key={activeId}
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.3 }}
              className="mb-6"
            >
              <p className="text-slate-500">
                <span
                  className="font-medium text-slate-700"
                  style={{ fontFamily: "Inter, sans-serif" }}
                >
                  {activeAgent.task || activeAgent.agentId}
                </span>{" "}
                &middot;{" "}
                <span className="capitalize">{activeAgent.status}</span> &middot;{" "}
                {activeAgent.totalTurns > 0 && (
                  <>
                    {activeAgent.totalTurns} turns &middot;{" "}
                  </>
                )}
                <span className="text-teal-600 font-medium">
                  {hypotheses.length} hypotheses
                </span>
                {activeAgent.childCount > 0 && (
                  <>
                    {" "}
                    &middot;{" "}
                    <span className="text-slate-500">
                      {activeAgent.childCount} subagents
                    </span>
                  </>
                )}
              </p>
            </motion.div>
          )}

          <HypothesisCardGrid key={activeId} hypotheses={hypotheses} />
        </div>
      </div>

      {/* Thinking sidebar */}
      <ThinkingSidebar
        open={thinkingOpen}
        onClose={() => setThinkingOpen(false)}
        events={events}
        connected={connected}
        agentId={activeId}
      />
    </div>
  );
}
