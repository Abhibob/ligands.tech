import { motion } from "framer-motion";
import type { Pair, Protein, Ligand } from "../../types";
import { getExplanation, getDetailedExplanation } from "../../data";

interface BindingAnalysisProps {
  pair: Pair;
  protein: Protein;
  ligand: Ligand;
}

const cardFade = {
  hidden: { opacity: 0, y: 12 },
  show: { opacity: 1, y: 0 },
};

export default function BindingAnalysis({ pair, protein, ligand }: BindingAnalysisProps) {
  const explanation = getExplanation(protein, ligand, pair.score, pair.explainIdx);
  const detailedExplanation = getDetailedExplanation(protein, ligand, pair.score, pair.explainIdx);

  const selectivityScore = Math.min(100, Math.max(0, pair.score + (pair.score > 50 ? 5 : -10)));
  const selectivityColor = selectivityScore >= 70 ? "bg-emerald-500" : selectivityScore >= 40 ? "bg-amber-500" : "bg-red-500";

  return (
    <div className="space-y-6">
      <motion.div
        className="grid grid-cols-1 sm:grid-cols-3 gap-4"
        initial="hidden"
        whileInView="show"
        viewport={{ once: true }}
        transition={{ staggerChildren: 0.1 }}
      >
        <motion.div variants={cardFade} className="bg-slate-50 rounded-lg p-4">
          <p className="text-xs text-slate-400 uppercase tracking-wide">Binding Energy</p>
          <p className="mt-1 text-xl font-semibold text-slate-900" style={{ fontFamily: "Inter, sans-serif" }}>{pair.bindingEnergy} kcal/mol</p>
        </motion.div>
        <motion.div variants={cardFade} className="bg-slate-50 rounded-lg p-4">
          <p className="text-xs text-slate-400 uppercase tracking-wide">Dissociation (Kd)</p>
          <p className="mt-1 text-xl font-semibold text-slate-900" style={{ fontFamily: "Inter, sans-serif" }}>{pair.kd}</p>
        </motion.div>
        <motion.div variants={cardFade} className="bg-slate-50 rounded-lg p-4">
          <p className="text-xs text-slate-400 uppercase tracking-wide">Key Residues</p>
          <div className="mt-1 flex flex-wrap gap-1">
            {pair.keyResidues.map((r) => (
              <span key={r} className="px-2 py-0.5 text-xs rounded bg-white border border-slate-200 text-slate-600 font-mono">
                {r}
              </span>
            ))}
          </div>
        </motion.div>
      </motion.div>

      {/* Structural Details */}
      <motion.div
        className="grid grid-cols-1 sm:grid-cols-2 gap-4"
        initial={{ opacity: 0, y: 12 }}
        whileInView={{ opacity: 1, y: 0 }}
        viewport={{ once: true }}
        transition={{ duration: 0.5, delay: 0.1 }}
      >
        <div className="bg-slate-50 rounded-lg p-4">
          <p className="text-xs text-slate-400 uppercase tracking-wide">Protein Type</p>
          <p className="mt-1 text-sm font-semibold text-slate-700" style={{ fontFamily: "Inter, sans-serif" }}>{protein.type}</p>
        </div>
        <div className="bg-slate-50 rounded-lg p-4">
          <p className="text-xs text-slate-400 uppercase tracking-wide">Ligand Type &middot; MW</p>
          <p className="mt-1 text-sm font-semibold text-slate-700" style={{ fontFamily: "Inter, sans-serif" }}>{ligand.type} &middot; {ligand.molecularWeight}</p>
        </div>
      </motion.div>

      {/* Selectivity Assessment */}
      <motion.div
        className="bg-white border border-slate-200 rounded-xl p-6"
        initial={{ opacity: 0, y: 12 }}
        whileInView={{ opacity: 1, y: 0 }}
        viewport={{ once: true }}
        transition={{ duration: 0.5, delay: 0.15 }}
      >
        <h3 className="text-sm font-semibold text-slate-900 uppercase tracking-wide mb-3" style={{ fontFamily: "Inter, sans-serif" }}>
          Selectivity Assessment
        </h3>
        <div className="flex items-center gap-4">
          <div className="flex-1">
            <div className="w-full bg-slate-100 rounded-full h-2.5 overflow-hidden">
              <motion.div
                className={`h-full rounded-full ${selectivityColor}`}
                initial={{ width: 0 }}
                whileInView={{ width: `${selectivityScore}%` }}
                viewport={{ once: true }}
                transition={{ duration: 1, ease: "easeOut", delay: 0.3 }}
              />
            </div>
          </div>
          <span className="text-sm font-semibold text-slate-700 w-10 text-right" style={{ fontFamily: "Inter, sans-serif" }}>
            {selectivityScore}%
          </span>
        </div>
        <p className="mt-2 text-xs text-slate-500">
          {selectivityScore >= 70
            ? "High selectivity — minimal off-target interactions expected"
            : selectivityScore >= 40
              ? "Moderate selectivity — some cross-reactivity with related targets"
              : "Low selectivity — significant off-target binding observed"}
        </p>
      </motion.div>

      {/* Binding Analysis */}
      <motion.div
        className="bg-white border border-slate-200 rounded-xl p-6"
        initial={{ opacity: 0, y: 12 }}
        whileInView={{ opacity: 1, y: 0 }}
        viewport={{ once: true }}
        transition={{ duration: 0.5, delay: 0.2 }}
      >
        <h3 className="text-sm font-semibold text-slate-900 uppercase tracking-wide mb-3" style={{ fontFamily: "Inter, sans-serif" }}>
          Binding Analysis
        </h3>
        <motion.p
          className="text-slate-600 leading-relaxed"
          initial={{ opacity: 0 }}
          whileInView={{ opacity: 1 }}
          viewport={{ once: true }}
          transition={{ duration: 0.6, delay: 0.3 }}
        >
          {explanation}
        </motion.p>
        <motion.p
          className="text-slate-600 leading-relaxed mt-4"
          initial={{ opacity: 0 }}
          whileInView={{ opacity: 1 }}
          viewport={{ once: true }}
          transition={{ duration: 0.6, delay: 0.5 }}
        >
          {detailedExplanation}
        </motion.p>
      </motion.div>
    </div>
  );
}
