import { Suspense } from "react";
import { Link } from "react-router-dom";
import { motion } from "framer-motion";
import ScoreRing from "../shared/ScoreRing";
import MiniBindingScene from "../three/MiniBindingScene";
import { deriveScore } from "../../utils/scores";
import type { Hypothesis } from "../../types";

interface HypothesisCardProps {
  hypothesis: Hypothesis;
}

export default function HypothesisCard({ hypothesis }: HypothesisCardProps) {
  const score = deriveScore(hypothesis.steps);
  const stepsDone = hypothesis.steps.filter(
    (s) => s.status === "succeeded" || s.status === "done"
  ).length;

  return (
    <Link to={`/hypothesis/${hypothesis.id}`}>
      <motion.div
        className="bg-white border border-slate-200 rounded-xl overflow-hidden flex flex-col hover:shadow-lg hover:border-teal-300 transition-all duration-300"
        whileHover={{ scale: 1.02, y: -4 }}
        transition={{ type: "spring", stiffness: 400, damping: 25 }}
      >
        <div className="relative h-44 bg-gradient-to-br from-slate-50 to-slate-100">
          <Suspense fallback={null}>
            <MiniBindingScene pairId={hypothesis.id} score={score} />
          </Suspense>
          <div className="absolute bottom-0 left-0 right-0 h-8 bg-gradient-to-t from-white to-transparent" />
        </div>

        <div className="p-4 flex-1 flex flex-col justify-between">
          <div className="flex items-start justify-between">
            <div>
              <span className="text-xs font-medium text-slate-400 uppercase tracking-wide">
                {hypothesis.status}
              </span>
              <h3
                className="text-lg font-semibold text-slate-900"
                style={{ fontFamily: "Inter, sans-serif" }}
              >
                {hypothesis.proteinName || "Unknown protein"}
              </h3>
              <p className="text-sm text-teal-600 font-medium">
                {hypothesis.ligandName || "Unknown ligand"}
              </p>
            </div>
            <ScoreRing score={score} size={48} />
          </div>

          <div className="mt-3">
            <div className="flex items-center justify-between text-xs text-slate-500">
              <span>
                {stepsDone}/{hypothesis.steps.length} steps complete
              </span>
              <span className="capitalize">{hypothesis.status}</span>
            </div>
            <div className="mt-1.5 w-full bg-slate-100 rounded-full h-1.5 overflow-hidden">
              <div
                className="h-full rounded-full bg-teal-500 transition-all duration-500"
                style={{
                  width: `${hypothesis.steps.length > 0 ? (stepsDone / hypothesis.steps.length) * 100 : 0}%`,
                }}
              />
            </div>
          </div>
        </div>
      </motion.div>
    </Link>
  );
}
