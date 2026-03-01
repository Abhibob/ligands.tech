import { useState, useEffect, useCallback } from "react";
import { useParams, useNavigate, Link } from "react-router-dom";
import { motion } from "framer-motion";
import { ArrowLeft, Brain } from "lucide-react";
import AgentSidebar from "../components/agents/AgentSidebar";
import HypothesisCardGrid from "../components/agents/HypothesisCardGrid";
import ThinkingSidebar from "../components/agents/ThinkingSidebar";
import Markdown from "../components/shared/Markdown";
import { useAgentEvents } from "../hooks/useAgentEvents";
import { api } from "../api/client";
import type { Agent, Hypothesis } from "../types";

export default function FinishedAgentsPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();

  const [agents, setAgents] = useState<Agent[]>([]);
  const [hypotheses, setHypotheses] = useState<Hypothesis[]>([]);
  const [loading, setLoading] = useState(true);
  const [thinkingOpen, setThinkingOpen] = useState(false);

  const activeId = id || agents[0]?.agentId || null;
  const activeAgent = agents.find((a) => a.agentId === activeId) || null;

  // WebSocket events (will replay history for finished agents)
  const { events, connected } = useAgentEvents(thinkingOpen ? activeId : null);

  // Load finished agents (completed, failed, max_turns)
  useEffect(() => {
    let cancelled = false;
    const load = async () => {
      try {
        const data = await api.listAgents(100, 0, "finished");
        if (!cancelled) {
          setAgents(data);
          setLoading(false);
        }
      } catch {
        if (!cancelled) setLoading(false);
      }
    };
    load();
    return () => {
      cancelled = true;
    };
  }, []);

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
  }, [loadHypotheses]);

  const handleChange = (agentId: string) => {
    navigate(`/finished/${agentId}`);
  };

  return (
    <div className="max-w-7xl mx-auto px-6 py-10">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-3xl font-bold text-slate-900">Finished Agents</h1>
        <div className="flex items-center gap-3">
          {activeAgent && (
            <button
              onClick={() => setThinkingOpen(true)}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 text-sm font-medium rounded-lg bg-slate-900 text-white hover:bg-slate-800 transition-colors"
            >
              <Brain className="w-4 h-4" />
              Show Thinking
            </button>
          )}
          <Link
            to="/agents"
            className="inline-flex items-center gap-1.5 text-sm text-slate-500 hover:text-teal-600 transition-colors"
          >
            <ArrowLeft className="w-4 h-4" />
            Running Agents
          </Link>
        </div>
      </div>
      <div className="flex gap-6 min-h-[calc(100vh-12rem)]">
        <AgentSidebar
          agents={agents}
          activeId={activeId}
          onChange={handleChange}
          loading={loading}
          emptyText="No finished agents"
        />

        <div className="flex-1 min-w-0">
          {activeAgent && (
            <motion.div
              key={activeId}
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.3 }}
              className="mb-6 space-y-3"
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
                {activeAgent.totalTurns} turns &middot;{" "}
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

              {activeAgent.finalResponse && (
                <div className="bg-slate-50 border border-slate-200 rounded-lg p-4">
                  <p className="text-xs text-slate-400 uppercase tracking-wide mb-2">
                    Agent Response
                  </p>
                  <Markdown>{activeAgent.finalResponse}</Markdown>
                </div>
              )}
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
