import { motion } from "framer-motion";
import ScoreRing from "../shared/ScoreRing";
import type { Protein, Ligand, Pair } from "../../types";

interface InteractionHeaderProps {
  protein: Protein;
  ligand: Ligand;
  pair: Pair;
}

export default function InteractionHeader({ protein, ligand, pair }: InteractionHeaderProps) {
  return (
    <motion.div
      className="bg-white border border-slate-200 rounded-xl p-6 flex items-center gap-6"
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5 }}
    >
      <ScoreRing score={pair.score} size={80} />
      <div>
        <h2 className="text-2xl font-bold text-slate-900">
          {protein.name} <span className="text-slate-400">+</span> {ligand.name}
        </h2>
        <p className="text-sm text-slate-500 mt-1">
          {protein.fullName} &middot; {ligand.type} ({ligand.molecularWeight})
        </p>
      </div>
    </motion.div>
  );
}
