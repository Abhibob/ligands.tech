import { Suspense, useState, useEffect } from "react";
import { useParams, Link } from "react-router-dom";
import { motion } from "framer-motion";
import { ArrowLeft } from "lucide-react";
import { api } from "../api/client";
import AnalysisPanel from "../components/interaction/AnalysisPanel";
import DetailBindingScene from "../components/three/DetailBindingScene";
import ScoreRing from "../components/shared/ScoreRing";
import { deriveScore, deriveBindingEnergy } from "../utils/scores";
import type { Hypothesis, Agent } from "../types";

const stagger = {
  hidden: { opacity: 0 },
  show: {
    opacity: 1,
    transition: { staggerChildren: 0.12 },
  },
};

const fadeUp = {
  hidden: { opacity: 0, y: 16 },
  show: { opacity: 1, y: 0, transition: { duration: 0.5, ease: "easeOut" as const } },
};

export default function HypothesisPage() {
  const { hypothesisId } = useParams<{ hypothesisId: string }>();
  const [hypothesis, setHypothesis] = useState<Hypothesis | null>(null);
  const [agent, setAgent] = useState<Agent | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!hypothesisId) return;
    let cancelled = false;

    const load = async () => {
      try {
        const hyp = await api.getHypothesis(hypothesisId);
        if (!cancelled) setHypothesis(hyp);
      } catch {
        // hypothesis not found
      } finally {
        if (!cancelled) setLoading(false);
      }
    };

    load();
    // Poll if hypothesis is still pending/running
    const interval = setInterval(load, 4000);
    return () => {
      cancelled = true;
      clearInterval(interval);
    };
  }, [hypothesisId]);

  // Load parent agent for final_response
  useEffect(() => {
    if (!hypothesis) return;
    // hypotheses have agent_id in the API but it's not exposed directly in the response yet
    // We'll use the agent_id from the URL or we'll fetch it via the hypothesis id
    // For now the agent's finalResponse is displayed if available
  }, [hypothesis]);

  if (loading) {
    return (
      <div className="max-w-6xl mx-auto px-6 py-10">
        <p className="text-slate-400">Loading hypothesis...</p>
      </div>
    );
  }

  if (!hypothesis) {
    return (
      <div className="max-w-6xl mx-auto px-6 py-10">
        <p className="text-slate-500">Hypothesis not found.</p>
        <Link to="/agents" className="text-teal-600 hover:underline mt-2 inline-block">
          Back to Agents
        </Link>
      </div>
    );
  }

  const score = deriveScore(hypothesis.steps);
  const energy = deriveBindingEnergy(hypothesis.steps);
  const proteinName = hypothesis.proteinName || "Unknown";
  const ligandName = hypothesis.ligandName || "Unknown";

  return (
    <div className="max-w-6xl mx-auto px-6 py-10">
      <Link
        to="/agents"
        className="inline-flex items-center gap-1.5 text-sm text-slate-500 hover:text-teal-600 mb-6 transition-colors"
      >
        <ArrowLeft className="w-4 h-4" />
        Back to Agents
      </Link>

      <motion.div variants={stagger} initial="hidden" animate="show" className="space-y-8">
        {/* Two-column: 3D left, summary right */}
        <motion.div variants={fadeUp} className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <Suspense
            fallback={
              <div className="h-[400px] rounded-xl bg-slate-50 flex items-center justify-center text-slate-400">
                Loading 3D scene...
              </div>
            }
          >
            <DetailBindingScene
              pairId={hypothesis.id}
              score={score}
              proteinName={proteinName}
              ligandName={ligandName}
            />
          </Suspense>

          <div className="flex flex-col justify-center space-y-6">
            <div className="flex items-center gap-5">
              <ScoreRing score={score} size={80} />
              <div>
                <h2 className="text-2xl font-bold text-slate-900">
                  {proteinName} <span className="text-slate-400">+</span> {ligandName}
                </h2>
                <p className="text-sm text-slate-500 mt-1 capitalize">{hypothesis.status}</p>
              </div>
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div className="bg-slate-50 rounded-lg p-3">
                <p className="text-xs text-slate-400 uppercase tracking-wide">Status</p>
                <p
                  className="mt-0.5 text-sm font-semibold text-slate-700 capitalize"
                  style={{ fontFamily: "Inter, sans-serif" }}
                >
                  {hypothesis.status}
                </p>
              </div>
              <div className="bg-slate-50 rounded-lg p-3">
                <p className="text-xs text-slate-400 uppercase tracking-wide">Steps</p>
                <p
                  className="mt-0.5 text-sm font-semibold text-slate-700"
                  style={{ fontFamily: "Inter, sans-serif" }}
                >
                  {hypothesis.steps.filter((s) => s.status === "succeeded" || s.status === "done").length}/
                  {hypothesis.steps.length}
                </p>
              </div>
              <div className="bg-slate-50 rounded-lg p-3">
                <p className="text-xs text-slate-400 uppercase tracking-wide">Composite Score</p>
                <p
                  className="mt-0.5 text-sm font-semibold text-slate-700"
                  style={{ fontFamily: "Inter, sans-serif" }}
                >
                  {score}/100
                </p>
              </div>
              <div className="bg-slate-50 rounded-lg p-3">
                <p className="text-xs text-slate-400 uppercase tracking-wide">Binding Energy</p>
                <p
                  className="mt-0.5 text-sm font-semibold text-slate-700"
                  style={{ fontFamily: "Inter, sans-serif" }}
                >
                  {energy != null ? `${energy} kcal/mol` : "—"}
                </p>
              </div>
            </div>
          </div>
        </motion.div>

        <motion.div variants={fadeUp}>
          <AnalysisPanel hypothesis={hypothesis} agentResponse={agent?.finalResponse || null} />
        </motion.div>
      </motion.div>
    </div>
  );
}
