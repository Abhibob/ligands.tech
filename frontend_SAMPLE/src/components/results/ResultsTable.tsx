import { useState, useMemo } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { ChevronUp, ChevronDown } from "lucide-react";
import { pairs } from "../../data";
import ResultsRow from "./ResultsRow";

type SortKey = "score" | "bindingEnergy";

export default function ResultsTable() {
  const [sortBy, setSortBy] = useState<SortKey>("score");
  const [sortAsc, setSortAsc] = useState(false);

  const sorted = useMemo(() => {
    return [...pairs].sort((a, b) => {
      const diff = sortBy === "score"
        ? b.score - a.score
        : a.bindingEnergy - b.bindingEnergy;
      return sortAsc ? -diff : diff;
    });
  }, [sortBy, sortAsc]);

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
        {sortAsc ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
      </motion.span>
    );
  };

  const maxScore = Math.max(...pairs.map((p) => p.score));

  return (
    <div className="bg-white border border-slate-200 rounded-xl overflow-hidden">
      <div className="overflow-x-auto">
        <table className="w-full">
          <thead>
            <tr className="bg-slate-50 border-b border-slate-200">
              <th className="py-3 px-4 text-left text-xs font-semibold text-slate-500 uppercase tracking-wide">#</th>
              <th className="py-3 px-4 text-left text-xs font-semibold text-slate-500 uppercase tracking-wide">Protein</th>
              <th className="py-3 px-4 text-left text-xs font-semibold text-slate-500 uppercase tracking-wide">Ligand</th>
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
              <th className="py-3 px-4 text-left text-xs font-semibold text-slate-500 uppercase tracking-wide">Kd</th>
              <th className="py-3 px-4 text-left text-xs font-semibold text-slate-500 uppercase tracking-wide">Researcher</th>
              <th className="py-3 px-4 text-left text-xs font-semibold text-slate-500 uppercase tracking-wide"></th>
            </tr>
          </thead>
          <AnimatePresence mode="popLayout">
            <tbody>
              {sorted.map((pair, i) => (
                <ResultsRow key={pair.id} pair={pair} rank={i + 1} index={i} maxScore={maxScore} />
              ))}
            </tbody>
          </AnimatePresence>
        </table>
      </div>
    </div>
  );
}
