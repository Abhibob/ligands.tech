import { motion } from 'framer-motion';
import { useNavigate } from 'react-router-dom';
import { Loader2 } from 'lucide-react';
import MiniMolecularViz from './MiniMolecularViz';
import { getProtein, getLigand, getScoreColor } from '../data/mockData';

export default function PairPreviewCard({ pair, isComplete, index = 0 }) {
  const navigate = useNavigate();
  const protein = getProtein(pair.proteinId);
  const ligand = getLigand(pair.ligandId);
  const isHighScore = pair.score > 70;

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{
        delay: index * 0.1,
        type: 'spring',
        stiffness: 300,
        damping: 24,
      }}
      whileHover={isComplete ? { y: -3, transition: { type: 'spring', stiffness: 400, damping: 20 } } : undefined}
      onClick={() => isComplete && navigate(`/interaction/${pair.id}`)}
      className={`relative rounded-xl border overflow-hidden transition-all ${
        isComplete
          ? 'border-border-subtle bg-bg-card hover:bg-bg-card-hover cursor-pointer'
          : 'border-border-subtle/50 bg-bg-card/50'
      }`}
      style={isComplete && isHighScore ? { borderLeftWidth: 3, borderLeftColor: 'var(--color-score-high)' } : undefined}
    >
      {/* Mini viz area */}
      <div className="flex items-center justify-center bg-black/20 py-3 px-2">
        {isComplete ? (
          <MiniMolecularViz
            proteinId={pair.proteinId}
            ligandId={pair.ligandId}
            score={pair.score}
          />
        ) : (
          <div className="flex items-center justify-center" style={{ width: 160, height: 100 }}>
            <Loader2 size={24} className="text-accent-blue animate-spin" />
          </div>
        )}
      </div>

      {/* Info section */}
      <div className="p-4">
        {/* Protein → Ligand badges */}
        <div className="flex items-center gap-2 mb-3">
          <span className="px-2 py-1 rounded-md bg-accent-purple/10 border border-accent-purple/20 text-accent-purple font-mono text-xs font-bold">
            {protein.name}
          </span>
          <span className="text-slate-600 text-xs">→</span>
          <span className="px-2 py-1 rounded-md bg-accent-blue/10 border border-accent-blue/20 text-accent-blue font-mono text-xs font-bold truncate">
            {ligand.name}
          </span>
        </div>

        {/* Score badge */}
        {isComplete ? (
          <motion.div
            initial={{ scale: 0 }}
            animate={{ scale: 1 }}
            transition={{ type: 'spring', stiffness: 500, damping: 15, delay: index * 0.1 + 0.3 }}
            className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-bold"
            style={{
              color: getScoreColor(pair.score),
              backgroundColor: `${getScoreColor(pair.score)}15`,
            }}
          >
            Score: {pair.score}
          </motion.div>
        ) : (
          <span className="text-[11px] text-slate-500 font-mono">Analyzing...</span>
        )}
      </div>
    </motion.div>
  );
}
