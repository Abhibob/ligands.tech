import { Suspense } from "react";
import { Link } from "react-router-dom";
import { motion } from "framer-motion";
import ScoreRing from "../shared/ScoreRing";
import MiniBindingScene from "../three/MiniBindingScene";
import { getProtein, getLigand } from "../../data";
import type { Pair } from "../../types";

interface PairCardProps {
  pair: Pair;
}

export default function PairCard({ pair }: PairCardProps) {
  const protein = getProtein(pair.proteinId);
  const ligand = getLigand(pair.ligandId);

  return (
    <Link to={`/interaction/${pair.id}`}>
      <motion.div
        className="bg-white border border-slate-200 rounded-xl overflow-hidden flex flex-col hover:shadow-lg hover:border-teal-300 transition-all duration-300"
        whileHover={{ scale: 1.02, y: -4 }}
        transition={{ type: "spring", stiffness: 400, damping: 25 }}
      >
        {/* 3D Mini Scene - upper ~55% */}
        <div className="relative h-44 bg-gradient-to-br from-slate-50 to-slate-100">
          <Suspense fallback={null}>
            <MiniBindingScene pairId={pair.id} score={pair.score} />
          </Suspense>
          {/* Gradient overlay at boundary */}
          <div className="absolute bottom-0 left-0 right-0 h-8 bg-gradient-to-t from-white to-transparent" />
        </div>

        {/* Info - lower ~45% */}
        <div className="p-4 flex-1 flex flex-col justify-between">
          <div>
            <div className="flex items-start justify-between">
              <div>
                <span className="text-xs font-medium text-slate-400 uppercase tracking-wide">
                  {protein.type}
                </span>
                <h3 className="text-lg font-semibold text-slate-900" style={{ fontFamily: "Inter, sans-serif" }}>
                  {protein.name}
                </h3>
                <p className="text-sm text-teal-600 font-medium">{ligand.name}</p>
              </div>
              <ScoreRing score={pair.score} size={48} />
            </div>
          </div>

          <div className="mt-3 space-y-2">
            <div className="flex items-center justify-between text-xs text-slate-500">
              <span>ΔG: {pair.bindingEnergy} kcal/mol</span>
              <span>Kd: {pair.kd}</span>
            </div>
            <div className="flex flex-wrap gap-1">
              {pair.keyResidues.slice(0, 3).map((r) => (
                <span
                  key={r}
                  className="px-1.5 py-0.5 text-[10px] rounded bg-slate-100 text-slate-500 font-mono"
                >
                  {r}
                </span>
              ))}
            </div>
          </div>
        </div>
      </motion.div>
    </Link>
  );
}
