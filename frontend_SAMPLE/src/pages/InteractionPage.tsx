import { Suspense } from "react";
import { useParams, Link } from "react-router-dom";
import { motion } from "framer-motion";
import { ArrowLeft } from "lucide-react";
import { getPair, getProtein, getLigand, getResearcher } from "../data";
import InteractionHeader from "../components/interaction/InteractionHeader";
import BindingAnalysis from "../components/interaction/BindingAnalysis";
import DetailBindingScene from "../components/three/DetailBindingScene";
import ScoreRing from "../components/shared/ScoreRing";

const stagger = {
  hidden: { opacity: 0 },
  show: {
    opacity: 1,
    transition: { staggerChildren: 0.12 },
  },
};

const fadeUp = {
  hidden: { opacity: 0, y: 16 },
  show: { opacity: 1, y: 0, transition: { duration: 0.5, ease: "easeOut" as const } },
};

export default function InteractionPage() {
  const { pairId } = useParams<{ pairId: string }>();
  const pair = getPair(pairId || "");

  if (!pair) {
    return (
      <div className="max-w-7xl mx-auto px-6 py-10">
        <p className="text-slate-500">Pair not found.</p>
        <Link to="/researchers" className="text-teal-600 hover:underline mt-2 inline-block">
          Back to Researchers
        </Link>
      </div>
    );
  }

  const protein = getProtein(pair.proteinId);
  const ligand = getLigand(pair.ligandId);
  const researcher = getResearcher(pair.researcherId);

  return (
    <div className="max-w-6xl mx-auto px-6 py-10">
      <Link
        to={`/researchers/${pair.researcherId}`}
        className="inline-flex items-center gap-1.5 text-sm text-slate-500 hover:text-teal-600 mb-6 transition-colors"
      >
        <ArrowLeft className="w-4 h-4" />
        Back to {researcher?.name}
      </Link>

      <motion.div
        variants={stagger}
        initial="hidden"
        animate="show"
        className="space-y-8"
      >
        {/* Two-column: 3D left, summary right */}
        <motion.div variants={fadeUp} className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <Suspense
            fallback={
              <div className="h-[400px] rounded-xl bg-slate-50 flex items-center justify-center text-slate-400">
                Loading 3D scene...
              </div>
            }
          >
            <DetailBindingScene
              pairId={pair.id}
              score={pair.score}
              proteinName={protein.name}
              ligandName={ligand.name}
            />
          </Suspense>

          <div className="flex flex-col justify-center space-y-6">
            <div className="flex items-center gap-5">
              <ScoreRing score={pair.score} size={80} />
              <div>
                <h2 className="text-2xl font-bold text-slate-900">
                  {protein.name} <span className="text-slate-400">+</span> {ligand.name}
                </h2>
                <p className="text-sm text-slate-500 mt-1">
                  {protein.fullName}
                </p>
              </div>
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div className="bg-slate-50 rounded-lg p-3">
                <p className="text-xs text-slate-400 uppercase tracking-wide">Type</p>
                <p className="mt-0.5 text-sm font-semibold text-slate-700" style={{ fontFamily: "Inter, sans-serif" }}>{protein.type}</p>
              </div>
              <div className="bg-slate-50 rounded-lg p-3">
                <p className="text-xs text-slate-400 uppercase tracking-wide">Ligand Type</p>
                <p className="mt-0.5 text-sm font-semibold text-slate-700" style={{ fontFamily: "Inter, sans-serif" }}>{ligand.type}</p>
              </div>
              <div className="bg-slate-50 rounded-lg p-3">
                <p className="text-xs text-slate-400 uppercase tracking-wide">Mol. Weight</p>
                <p className="mt-0.5 text-sm font-semibold text-slate-700" style={{ fontFamily: "Inter, sans-serif" }}>{ligand.molecularWeight}</p>
              </div>
              <div className="bg-slate-50 rounded-lg p-3">
                <p className="text-xs text-slate-400 uppercase tracking-wide">Binding Energy</p>
                <p className="mt-0.5 text-sm font-semibold text-slate-700" style={{ fontFamily: "Inter, sans-serif" }}>{pair.bindingEnergy} kcal/mol</p>
              </div>
            </div>

            <div className="flex flex-wrap gap-2">
              {pair.keyResidues.map((r) => (
                <span
                  key={r}
                  className="px-2.5 py-1 text-xs rounded-lg bg-teal-50 text-teal-700 border border-teal-200 font-mono"
                >
                  {r}
                </span>
              ))}
            </div>
          </div>
        </motion.div>

        <motion.div variants={fadeUp}>
          <BindingAnalysis pair={pair} protein={protein} ligand={ligand} />
        </motion.div>

        {researcher && (
          <motion.p variants={fadeUp} className="text-sm text-slate-400 text-right">
            Analyzed by {researcher.name}
          </motion.p>
        )}
      </motion.div>
    </div>
  );
}
