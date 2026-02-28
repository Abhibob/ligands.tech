import { motion } from "framer-motion";
import ResultsTable from "../components/results/ResultsTable";

export default function ResultsPage() {
  return (
    <div className="max-w-7xl mx-auto px-6 py-10">
      <motion.div
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5 }}
      >
        <h1 className="text-3xl font-bold text-slate-900 mb-2">Results</h1>
        <p className="text-slate-500 mb-8" style={{ fontFamily: "Inter, sans-serif" }}>
          All 17 protein-ligand pairs ranked by compatibility score.
        </p>
      </motion.div>
      <motion.div
        initial={{ opacity: 0, y: 16 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5, delay: 0.15 }}
      >
        <ResultsTable />
      </motion.div>
    </div>
  );
}
