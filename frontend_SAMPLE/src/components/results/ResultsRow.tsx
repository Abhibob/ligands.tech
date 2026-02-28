import { Link } from "react-router-dom";
import { motion } from "framer-motion";
import ScoreBadge from "../shared/ScoreBadge";
import { getProtein, getLigand, getResearcher } from "../../data";
import type { Pair } from "../../types";
import { ExternalLink } from "lucide-react";

interface ResultsRowProps {
  pair: Pair;
  rank: number;
  index: number;
  maxScore: number;
}

export default function ResultsRow({ pair, rank, index, maxScore }: ResultsRowProps) {
  const protein = getProtein(pair.proteinId);
  const ligand = getLigand(pair.ligandId);
  const researcher = getResearcher(pair.researcherId);

  const barWidth = (pair.score / maxScore) * 100;
  const barColor = pair.score >= 70 ? "bg-emerald-400" : pair.score >= 40 ? "bg-amber-400" : "bg-red-400";

  return (
    <motion.tr
      className="border-b border-slate-100 hover:bg-slate-50/80 transition-colors group relative"
      initial={{ opacity: 0, x: -12 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{ duration: 0.35, delay: index * 0.03 }}
    >
      <td className="py-3 px-4 text-sm text-slate-400 font-medium relative">
        <span className="absolute left-0 top-1 bottom-1 w-0.5 rounded-full bg-teal-500 opacity-0 group-hover:opacity-100 transition-opacity" />
        {rank}
      </td>
      <td className="py-3 px-4 text-sm font-semibold text-slate-900">{protein.name}</td>
      <td className="py-3 px-4 text-sm text-slate-700">{ligand.name}</td>
      <td className="py-3 px-4">
        <div className="flex items-center gap-2">
          <ScoreBadge score={pair.score} />
          <div className="w-12 h-1.5 bg-slate-100 rounded-full overflow-hidden">
            <div
              className={`h-full rounded-full ${barColor}`}
              style={{ width: `${barWidth}%` }}
            />
          </div>
        </div>
      </td>
      <td className="py-3 px-4 text-sm text-slate-600">{pair.bindingEnergy} kcal/mol</td>
      <td className="py-3 px-4 text-sm text-slate-600">{pair.kd}</td>
      <td className="py-3 px-4 text-sm text-slate-500">{researcher?.name}</td>
      <td className="py-3 px-4">
        <Link to={`/interaction/${pair.id}`} className="text-teal-600 hover:text-teal-700">
          <ExternalLink className="w-4 h-4" />
        </Link>
      </td>
    </motion.tr>
  );
}
