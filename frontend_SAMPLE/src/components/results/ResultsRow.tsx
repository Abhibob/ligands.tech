import { Link } from "react-router-dom";
import { motion } from "framer-motion";
import ScoreBadge from "../shared/ScoreBadge";
import { ExternalLink } from "lucide-react";
import type { Hypothesis } from "../../types";

interface ResultsRowProps {
  hypothesis: Hypothesis;
  score: number;
  bindingEnergy: number | null;
  agentTask: string;
  rank: number;
  index: number;
  maxScore: number;
}

export default function ResultsRow({
  hypothesis,
  score,
  bindingEnergy,
  agentTask,
  rank,
  index,
  maxScore,
}: ResultsRowProps) {
  const barWidth = maxScore > 0 ? (score / maxScore) * 100 : 0;
  const barColor =
    score >= 70 ? "bg-emerald-400" : score >= 40 ? "bg-amber-400" : "bg-red-400";

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
      <td className="py-3 px-4 text-sm font-semibold text-slate-900">
        {hypothesis.proteinName || "—"}
      </td>
      <td className="py-3 px-4 text-sm text-slate-700">
        {hypothesis.ligandName || "—"}
      </td>
      <td className="py-3 px-4">
        <div className="flex items-center gap-2">
          <ScoreBadge score={score} />
          <div className="w-12 h-1.5 bg-slate-100 rounded-full overflow-hidden">
            <div
              className={`h-full rounded-full ${barColor}`}
              style={{ width: `${barWidth}%` }}
            />
          </div>
        </div>
      </td>
      <td className="py-3 px-4 text-sm text-slate-600">
        {bindingEnergy != null ? `${bindingEnergy} kcal/mol` : "—"}
      </td>
      <td className="py-3 px-4 text-sm text-slate-500 truncate max-w-[150px]">
        {agentTask}
      </td>
      <td className="py-3 px-4">
        <Link
          to={`/hypothesis/${hypothesis.id}`}
          className="text-teal-600 hover:text-teal-700"
        >
          <ExternalLink className="w-4 h-4" />
        </Link>
      </td>
    </motion.tr>
  );
}
