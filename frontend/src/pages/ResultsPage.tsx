import { useState, useEffect } from "react";
import { motion } from "framer-motion";
import ResultsTable from "../components/results/ResultsTable";
import { api } from "../api/client";
import type { Agent, Hypothesis } from "../types";

export default function ResultsPage() {
  const [agents, setAgents] = useState<Agent[]>([]);
  const [allHypotheses, setAllHypotheses] = useState<
    (Hypothesis & { agentTask: string })[]
  >([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    const load = async () => {
      try {
        const agentList = await api.listAgents(100);
        if (cancelled) return;
        setAgents(agentList);

        const results: (Hypothesis & { agentTask: string })[] = [];
        for (const agent of agentList) {
          const hyps = await api.getAgentHypotheses(agent.agentId);
          for (const h of hyps) {
            results.push({ ...h, agentTask: agent.task || agent.agentId });
          }
        }
        if (!cancelled) {
          setAllHypotheses(results);
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

  return (
    <div className="max-w-7xl mx-auto px-6 py-10">
      <motion.div
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5 }}
      >
        <h1 className="text-3xl font-bold text-slate-900 mb-2">Results</h1>
        <p
          className="text-slate-500 mb-8"
          style={{ fontFamily: "Inter, sans-serif" }}
        >
          {loading
            ? "Loading hypotheses..."
            : `${allHypotheses.length} hypotheses across ${agents.length} agents, ranked by composite score.`}
        </p>
      </motion.div>
      <motion.div
        initial={{ opacity: 0, y: 16 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5, delay: 0.15 }}
      >
        <ResultsTable hypotheses={allHypotheses} loading={loading} />
      </motion.div>
    </div>
  );
}
