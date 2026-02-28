import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import { Trophy, ChevronDown, ChevronUp, BarChart3, Layers } from 'lucide-react';
import ScoreBar from '../components/ScoreBar';
import { getRankedPairs, getProtein, getLigand, getExplanation, getScoreColor, pairs } from '../data/mockData';
import { tableRow, slideFromLeft, scaleIn } from '../lib/animations';

const rankMedals = ['#f59e0b', '#94a3b8', '#cd7f32']; // gold, silver, bronze

export default function ResultsPage() {
  const navigate = useNavigate();
  const ranked = getRankedPairs();
  const [expanded, setExpanded] = useState(null);

  const avgScore = Math.round(pairs.reduce((s, p) => s + p.score, 0) / pairs.length);
  const topPair = ranked[0];
  const topProtein = getProtein(topPair.proteinId);
  const topLigand = getLigand(topPair.ligandId);

  return (
    <div className="max-w-5xl mx-auto px-6 py-10">
      <motion.div
        className="mb-8"
        variants={slideFromLeft}
        initial="hidden"
        animate="show"
      >
        <h1 className="text-2xl font-bold text-white mb-2">Compatibility Rankings</h1>
        <p className="text-slate-400">All protein-ligand pairs ranked by binding compatibility.</p>
      </motion.div>

      {/* Stats — differentiated cards */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-8">
        {/* Total Pairs — card-inset */}
        <motion.div
          initial={{ opacity: 0, scale: 0.92 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ type: 'spring', stiffness: 300, damping: 22 }}
          className="rounded-xl bg-bg-card p-5 card-inset"
        >
          <div className="flex items-center gap-2 mb-1">
            <Layers size={14} className="text-slate-500" />
            <p className="text-slate-500 text-xs uppercase tracking-wider">Total Pairs</p>
          </div>
          <p className="text-2xl font-bold text-white">{pairs.length}</p>
        </motion.div>

        {/* Avg Score — colored left border + mini score bar */}
        <motion.div
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1, type: 'spring', stiffness: 300, damping: 22 }}
          className="rounded-xl bg-bg-card p-5 border border-border-subtle"
          style={{ borderLeftWidth: 3, borderLeftColor: getScoreColor(avgScore) }}
        >
          <p className="text-slate-500 text-xs uppercase tracking-wider mb-1">Average Score</p>
          <p className="text-2xl font-bold mb-2" style={{ color: getScoreColor(avgScore) }}>{avgScore}</p>
          <ScoreBar score={avgScore} height={4} />
        </motion.div>

        {/* Top Candidate — accent-top + trophy, wider */}
        <motion.div
          initial={{ opacity: 0, x: 20 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ delay: 0.2, type: 'spring', stiffness: 260, damping: 20 }}
          className="rounded-xl bg-bg-card p-5 accent-top"
        >
          <div className="flex items-center gap-2 mb-1">
            <Trophy size={14} className="text-amber-400" />
            <p className="text-slate-500 text-xs uppercase tracking-wider">Top Candidate</p>
          </div>
          <p className="text-lg font-bold text-cyan-glow">
            {topProtein.name} + {topLigand.name}
          </p>
          <p className="text-xs text-slate-500 mt-0.5">Score: {topPair.score}</p>
        </motion.div>
      </div>

      {/* Rankings table */}
      <div className="rounded-xl border border-border-subtle bg-bg-card overflow-hidden">
        <div className="grid grid-cols-[3rem_1fr_1fr_10rem_3.5rem_2.5rem] gap-4 px-5 py-3 border-b border-border-subtle text-xs text-slate-500 uppercase tracking-wider font-medium">
          <span>Rank</span>
          <span>Protein</span>
          <span>Ligand</span>
          <span>Score</span>
          <span></span>
          <span></span>
        </div>

        {ranked.map((pair, i) => {
          const protein = getProtein(pair.proteinId);
          const ligand = getLigand(pair.ligandId);
          const isExpanded = expanded === pair.id;
          const rowVariants = tableRow(i);
          const medalColor = i < 3 ? rankMedals[i] : null;

          return (
            <motion.div
              key={pair.id}
              variants={rowVariants}
              initial="hidden"
              animate="show"
            >
              <div
                className={`grid grid-cols-[3rem_1fr_1fr_10rem_3.5rem_2.5rem] gap-4 px-5 py-4 items-center border-b border-border-subtle/50 transition-colors ${
                  isExpanded ? 'bg-bg-card-hover' : 'hover:bg-bg-card-hover'
                } ${i % 2 === 1 ? 'bg-white/[0.01]' : ''}`}
              >
                <span className="font-bold font-mono text-sm flex items-center gap-1.5">
                  {medalColor ? (
                    <span
                      className="w-5 h-5 rounded-full flex items-center justify-center text-[10px] font-bold"
                      style={{ backgroundColor: `${medalColor}20`, color: medalColor }}
                    >
                      {i + 1}
                    </span>
                  ) : (
                    <span className="text-slate-500">#{i + 1}</span>
                  )}
                </span>
                <span className="text-white font-medium text-sm">{protein.name}
                  <span className="text-slate-500 text-xs ml-1.5 hidden sm:inline">{protein.type}</span>
                </span>
                <span className="text-white font-medium text-sm">{ligand.name}
                  <span className="text-slate-500 text-xs ml-1.5 hidden sm:inline">{ligand.type}</span>
                </span>
                <ScoreBar score={pair.score} showLabel />
                <button
                  onClick={() => setExpanded(isExpanded ? null : pair.id)}
                  className="bg-transparent border-0 cursor-pointer text-slate-400 hover:text-white transition-colors p-0"
                >
                  {isExpanded ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
                </button>
                <button
                  onClick={() => navigate(`/interaction/${pair.id}`)}
                  className="bg-transparent border-0 cursor-pointer text-slate-400 hover:text-cyan-glow transition-colors p-0"
                  title="View interaction"
                >
                  <BarChart3 size={16} />
                </button>
              </div>

              <AnimatePresence>
                {isExpanded && (
                  <motion.div
                    initial={{ height: 0, opacity: 0 }}
                    animate={{ height: 'auto', opacity: 1 }}
                    exit={{ height: 0, opacity: 0 }}
                    transition={{ duration: 0.2 }}
                    className="overflow-hidden"
                  >
                    <div className="px-5 py-4 bg-bg-secondary/50 border-b border-border-subtle/50 text-sm text-slate-300 leading-relaxed accent-left">
                      {getExplanation(pair)}
                    </div>
                  </motion.div>
                )}
              </AnimatePresence>
            </motion.div>
          );
        })}
      </div>
    </div>
  );
}
