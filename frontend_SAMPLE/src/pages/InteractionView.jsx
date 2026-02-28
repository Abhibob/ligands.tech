import { useParams, Link } from 'react-router-dom';
import { motion } from 'framer-motion';
import { ArrowLeft, Zap, Atom, TestTube, Sparkles } from 'lucide-react';
import MolecularViz from '../components/MolecularViz';
import { getPair, getProtein, getLigand, getExplanation, getScoreColor, getScoreLabel } from '../data/mockData';

export default function InteractionView() {
  const { pairId } = useParams();
  const pair = getPair(pairId);

  if (!pair) {
    return (
      <div className="max-w-5xl mx-auto px-6 py-10 text-center text-slate-400">
        Pair not found.
      </div>
    );
  }

  const protein = getProtein(pair.proteinId);
  const ligand = getLigand(pair.ligandId);
  const explanation = getExplanation(pair);
  const scoreColor = getScoreColor(pair.score);

  // SVG circular ring for score card background
  const ringSize = 120;
  const ringR = 50;
  const ringCirc = 2 * Math.PI * ringR;
  const ringFill = ringCirc * (1 - pair.score / 100);

  return (
    <div className="max-w-5xl mx-auto px-6 py-10">
      <Link
        to={`/agents/${pair.agentId}`}
        className="inline-flex items-center gap-2 text-sm text-slate-400 hover:text-white transition-colors mb-8 no-underline"
      >
        <ArrowLeft size={16} />
        Back to Agent
      </Link>

      <motion.div
        initial={{ opacity: 0, x: -20 }}
        animate={{ opacity: 1, x: 0 }}
        transition={{ type: 'spring', stiffness: 260, damping: 20 }}
        className="mb-8"
      >
        <h1 className="text-2xl font-bold text-white mb-1">
          {protein.name} <span className="text-slate-500 font-normal mx-2">&times;</span> {ligand.name}
        </h1>
        <p className="text-slate-400 text-sm">
          {protein.fullName} &mdash; {ligand.type}
        </p>
      </motion.div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Viz — fades in first */}
        <motion.div
          className="lg:col-span-2"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ duration: 0.6 }}
        >
          <MolecularViz
            score={pair.score}
            proteinName={protein.name}
            ligandName={ligand.name}
          />
        </motion.div>

        {/* Score + details — 3 visually different cards */}
        <div className="flex flex-col gap-4">
          {/* 1. Score card: gradient bg, no border, SVG ring */}
          <motion.div
            initial={{ opacity: 0, scale: 0.85 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ delay: 0.35, type: 'spring', stiffness: 350, damping: 22 }}
            className="rounded-xl p-6 text-center relative overflow-hidden"
            style={{
              background: 'linear-gradient(135deg, #1a2235 0%, #1e2a45 50%, #1a2035 100%)',
            }}
          >
            {/* Background ring decoration */}
            <svg
              className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 opacity-20"
              width={ringSize}
              height={ringSize}
              viewBox={`0 0 ${ringSize} ${ringSize}`}
            >
              <circle cx={ringSize / 2} cy={ringSize / 2} r={ringR} fill="none" stroke="rgba(255,255,255,0.05)" strokeWidth="6" />
              <circle
                cx={ringSize / 2}
                cy={ringSize / 2}
                r={ringR}
                fill="none"
                stroke={scoreColor}
                strokeWidth="6"
                strokeLinecap="round"
                strokeDasharray={ringCirc}
                strokeDashoffset={ringFill}
                transform={`rotate(-90 ${ringSize / 2} ${ringSize / 2})`}
              />
            </svg>
            <p className="text-slate-400 text-xs uppercase tracking-wider mb-2 relative z-10">Compatibility Score</p>
            <div
              className="text-7xl font-bold font-mono relative z-10"
              style={{ color: scoreColor }}
            >
              {pair.score}
            </div>
            <div
              className="mt-2 inline-block px-3 py-1 rounded-full text-xs font-medium relative z-10"
              style={{
                color: scoreColor,
                backgroundColor: `${scoreColor}15`,
              }}
            >
              {getScoreLabel(pair.score)} Affinity
            </div>
          </motion.div>

          {/* 2. Binding details: accent-top treatment */}
          <motion.div
            initial={{ opacity: 0, x: 30 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: 0.5, type: 'spring', stiffness: 260, damping: 20 }}
            className="rounded-xl bg-bg-card p-5 accent-top"
          >
            <h3 className="text-white font-semibold text-sm mb-4 flex items-center gap-2">
              <Zap size={14} className="text-cyan-glow" />
              Binding Details
            </h3>
            <div className="flex flex-col gap-3 text-sm">
              <div className="flex justify-between">
                <span className="text-slate-400">Binding Energy</span>
                <span className="text-white font-mono">{pair.bindingEnergy} kcal/mol</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-400">Affinity (Kd)</span>
                <span className="text-white font-mono">{pair.affinityKd}</span>
              </div>
              <div>
                <span className="text-slate-400 block mb-1.5">Key Residues</span>
                <div className="flex flex-wrap gap-1.5">
                  {pair.keyResidues.map(r => (
                    <span
                      key={r}
                      className="px-2 py-0.5 rounded bg-accent-purple/10 border border-accent-purple/20 text-accent-purple text-xs font-mono"
                    >
                      {r}
                    </span>
                  ))}
                </div>
              </div>
            </div>
          </motion.div>

          {/* 3. Pair info: card-inset treatment */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.6, duration: 0.4 }}
            className="rounded-xl bg-bg-card p-5 card-inset"
          >
            <div className="flex flex-col gap-3 text-sm">
              <div className="flex items-center gap-2">
                <Atom size={14} className="text-accent-purple" />
                <span className="text-slate-400">Protein:</span>
                <span className="text-white font-medium">{protein.fullName}</span>
              </div>
              <div className="flex items-center gap-2">
                <TestTube size={14} className="text-accent-blue" />
                <span className="text-slate-400">Ligand:</span>
                <span className="text-white font-medium">{ligand.name} ({ligand.mw})</span>
              </div>
            </div>
          </motion.div>
        </div>
      </div>

      {/* Explanation — slides up */}
      <motion.div
        initial={{ opacity: 0, y: 24 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.7, type: 'spring', stiffness: 200, damping: 20 }}
        className="mt-6 rounded-xl bg-bg-card p-8 accent-left"
      >
        <div className="flex items-center gap-2 mb-1">
          <Sparkles size={14} className="text-cyan-glow" />
          <span className="text-xs text-slate-500 uppercase tracking-wider font-medium">AI Analysis</span>
        </div>
        <h3 className="text-white font-semibold mb-3 text-lg">Analysis Summary</h3>
        <p className="text-slate-300 leading-relaxed text-[15px]">{explanation}</p>
      </motion.div>
    </div>
  );
}
