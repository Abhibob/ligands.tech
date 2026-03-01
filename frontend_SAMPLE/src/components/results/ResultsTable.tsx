import { useState, useMemo } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { ChevronUp, ChevronDown, Loader2 } from "lucide-react";
import ResultsRow from "./ResultsRow";
import { deriveScore, deriveBindingEnergy } from "../../utils/scores";
import type { Hypothesis } from "../../types";

type SortKey = "score" | "bindingEnergy";

interface ResultsTableProps {
  hypotheses: (Hypothesis & { agentTask: string })[];
  loading?: boolean;
}

export default function ResultsTable({ hypotheses, loading }: ResultsTableProps) {
  const [sortBy, setSortBy] = useState<SortKey>("score");
  const [sortAsc, setSortAsc] = useState(false);

  const enriched = useMemo(
    () =>
      hypotheses.map((h) => ({
        ...h,
        score: deriveScore(h.steps),
        bindingEnergy: deriveBindingEnergy(h.steps),
      })),
    [hypotheses]
  );

  const sorted = useMemo(() => {
    return [...enriched].sort((a, b) => {
      const diff =
        sortBy === "score"
          ? b.score - a.score
          : (a.bindingEnergy ?? 0) - (b.bindingEnergy ?? 0);
      return sortAsc ? -diff : diff;
    });
  }, [enriched, sortBy, sortAsc]);

  const handleSort = (key: SortKey) => {
    if (sortBy === key) {
      setSortAsc(!sortAsc);
    } else {
      setSortBy(key);
      setSortAsc(false);
    }
  };

  const SortArrow = ({ columnKey }: { columnKey: SortKey }) => {
    if (sortBy !== columnKey) return null;
    return (
      <motion.span
        key={sortAsc ? "asc" : "desc"}
        initial={{ rotate: sortAsc ? 180 : 0, opacity: 0 }}
        animate={{ rotate: 0, opacity: 1 }}
        className="inline-flex ml-1"
      >
        {sortAsc ? (
          <ChevronUp className="w-3.5 h-3.5" />
        ) : (
          <ChevronDown className="w-3.5 h-3.5" />
        )}
      </motion.span>
    );
  };

  const maxScore = Math.max(1, ...enriched.map((h) => h.score));

  if (loading) {
    return (
      <div className="flex items-center justify-center py-16 text-slate-400">
        <Loader2 className="w-6 h-6 animate-spin" />
      </div>
    );
  }

  if (sorted.length === 0) {
    return (
      <p className="text-slate-400 text-sm py-8">No hypotheses found.</p>
    );
  }

  return (
    <div className="bg-white border border-slate-200 rounded-xl overflow-hidden">
      <div className="overflow-x-auto">
        <table className="w-full">
          <thead>
            <tr className="bg-slate-50 border-b border-slate-200">
              <th className="py-3 px-4 text-left text-xs font-semibold text-slate-500 uppercase tracking-wide">
                #
              </th>
              <th className="py-3 px-4 text-left text-xs font-semibold text-slate-500 uppercase tracking-wide">
                Protein
              </th>
              <th className="py-3 px-4 text-left text-xs font-semibold text-slate-500 uppercase tracking-wide">
                Ligand
              </th>
              <th
                className="py-3 px-4 text-left text-xs font-semibold text-slate-500 uppercase tracking-wide cursor-pointer hover:text-slate-700 select-none"
                onClick={() => handleSort("score")}
              >
                <span className="inline-flex items-center">
                  Score
                  <SortArrow columnKey="score" />
                </span>
              </th>
              <th
                className="py-3 px-4 text-left text-xs font-semibold text-slate-500 uppercase tracking-wide cursor-pointer hover:text-slate-700 select-none"
                onClick={() => handleSort("bindingEnergy")}
              >
                <span className="inline-flex items-center">
                  Binding Energy
                  <SortArrow columnKey="bindingEnergy" />
                </span>
              </th>
              <th className="py-3 px-4 text-left text-xs font-semibold text-slate-500 uppercase tracking-wide">
                Agent
              </th>
              <th className="py-3 px-4 text-left text-xs font-semibold text-slate-500 uppercase tracking-wide" />
            </tr>
          </thead>
          <AnimatePresence mode="popLayout">
            <tbody>
              {sorted.map((h, i) => (
                <ResultsRow
                  key={h.id}
                  hypothesis={h}
                  score={h.score}
                  bindingEnergy={h.bindingEnergy}
                  agentTask={h.agentTask}
                  rank={i + 1}
                  index={i}
                  maxScore={maxScore}
                />
              ))}
            </tbody>
          </AnimatePresence>
        </table>
      </div>
    </div>
  );
}
