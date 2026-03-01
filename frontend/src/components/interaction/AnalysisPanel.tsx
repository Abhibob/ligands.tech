import { motion } from "framer-motion";
import { CheckCircle2, XCircle, Clock, Loader2 } from "lucide-react";
import type { Hypothesis } from "../../types";
import { deriveBindingEnergy, deriveKeyResidues } from "../../utils/scores";
import Markdown from "../shared/Markdown";

interface AnalysisPanelProps {
  hypothesis: Hypothesis;
  agentResponse: string | null;
}

const stepLabels: Record<string, string> = {
  resolve_protein: "Protein Resolution",
  resolve_ligand: "Ligand Resolution",
  boltz_predict: "Boltz-2 Prediction",
  gnina_dock: "GNINA Docking",
  posebusters_check: "PoseBusters Validation",
  plip_profile: "PLIP Interaction Profile",
};

const stepStatusIcon = {
  succeeded: CheckCircle2,
  done: CheckCircle2,
  failed: XCircle,
  running: Loader2,
  pending: Clock,
};

const stepStatusColor = {
  succeeded: "text-emerald-500",
  done: "text-emerald-500",
  failed: "text-red-500",
  running: "text-teal-500",
  pending: "text-slate-400",
};

const cardFade = {
  hidden: { opacity: 0, y: 12 },
  show: { opacity: 1, y: 0 },
};

export default function AnalysisPanel({ hypothesis, agentResponse }: AnalysisPanelProps) {
  const energy = deriveBindingEnergy(hypothesis.steps);
  const residues = deriveKeyResidues(hypothesis.steps);

  return (
    <div className="space-y-6">
      {/* Metrics row */}
      <motion.div
        className="grid grid-cols-1 sm:grid-cols-3 gap-4"
        initial="hidden"
        whileInView="show"
        viewport={{ once: true }}
        transition={{ staggerChildren: 0.1 }}
      >
        <motion.div variants={cardFade} className="bg-slate-50 rounded-lg p-4">
          <p className="text-xs text-slate-400 uppercase tracking-wide">Binding Energy</p>
          <p
            className="mt-1 text-xl font-semibold text-slate-900"
            style={{ fontFamily: "Inter, sans-serif" }}
          >
            {energy != null ? `${energy} kcal/mol` : "—"}
          </p>
        </motion.div>
        <motion.div variants={cardFade} className="bg-slate-50 rounded-lg p-4">
          <p className="text-xs text-slate-400 uppercase tracking-wide">Pipeline Steps</p>
          <p
            className="mt-1 text-xl font-semibold text-slate-900"
            style={{ fontFamily: "Inter, sans-serif" }}
          >
            {hypothesis.steps.filter((s) => s.status === "succeeded" || s.status === "done").length}
            /{hypothesis.steps.length} done
          </p>
        </motion.div>
        <motion.div variants={cardFade} className="bg-slate-50 rounded-lg p-4">
          <p className="text-xs text-slate-400 uppercase tracking-wide">Key Residues</p>
          <div className="mt-1 flex flex-wrap gap-1">
            {residues.length > 0 ? (
              residues.map((r) => (
                <span
                  key={r}
                  className="px-2 py-0.5 text-xs rounded bg-white border border-slate-200 text-slate-600 font-mono"
                >
                  {r}
                </span>
              ))
            ) : (
              <span className="text-sm text-slate-400">—</span>
            )}
          </div>
        </motion.div>
      </motion.div>

      {/* Pipeline steps */}
      <motion.div
        className="bg-white border border-slate-200 rounded-xl p-6"
        initial={{ opacity: 0, y: 12 }}
        whileInView={{ opacity: 1, y: 0 }}
        viewport={{ once: true }}
        transition={{ duration: 0.5, delay: 0.1 }}
      >
        <h3
          className="text-sm font-semibold text-slate-900 uppercase tracking-wide mb-4"
          style={{ fontFamily: "Inter, sans-serif" }}
        >
          Pipeline Steps
        </h3>
        <div className="space-y-3">
          {hypothesis.steps.map((step) => {
            const Icon =
              stepStatusIcon[step.status as keyof typeof stepStatusIcon] || Clock;
            const color =
              stepStatusColor[step.status as keyof typeof stepStatusColor] || "text-slate-400";
            return (
              <div
                key={step.id}
                className="flex items-center justify-between py-2 border-b border-slate-100 last:border-0"
              >
                <div className="flex items-center gap-3">
                  <Icon
                    className={`w-4 h-4 ${color} ${step.status === "running" ? "animate-spin" : ""}`}
                  />
                  <span className="text-sm font-medium text-slate-700">
                    {stepLabels[step.stepName] || step.stepName}
                  </span>
                </div>
                <div className="flex items-center gap-3 text-xs text-slate-500">
                  {step.runtimeSeconds != null && (
                    <span>{step.runtimeSeconds.toFixed(1)}s</span>
                  )}
                  <span className="capitalize">{step.status}</span>
                </div>
              </div>
            );
          })}
          {hypothesis.steps.length === 0 && (
            <p className="text-sm text-slate-400">No pipeline steps recorded yet.</p>
          )}
        </div>
      </motion.div>

      {/* Agent analysis */}
      {agentResponse && (
        <motion.div
          className="bg-white border border-slate-200 rounded-xl p-6"
          initial={{ opacity: 0, y: 12 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.5, delay: 0.2 }}
        >
          <h3
            className="text-sm font-semibold text-slate-900 uppercase tracking-wide mb-3"
            style={{ fontFamily: "Inter, sans-serif" }}
          >
            Agent Analysis
          </h3>
          <Markdown>{agentResponse}</Markdown>
        </motion.div>
      )}
    </div>
  );
}
