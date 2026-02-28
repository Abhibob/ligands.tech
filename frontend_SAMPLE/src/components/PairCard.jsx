import { motion } from 'framer-motion';
import { useNavigate } from 'react-router-dom';
import { ArrowRight, Loader2, CheckCircle2 } from 'lucide-react';
import { getProtein, getLigand, getScoreColor } from '../data/mockData';

export default function PairCard({ pair, isComplete, index }) {
  const navigate = useNavigate();
  const protein = getProtein(pair.proteinId);
  const ligand = getLigand(pair.ligandId);
  const isEven = index % 2 === 0;
  const isHighScore = pair.score > 70;

  return (
    <motion.div
      initial={isEven ? { opacity: 0, x: -16 } : { opacity: 0, scale: 0.96 }}
      animate={{ opacity: 1, x: 0, scale: 1 }}
      transition={{
        delay: index * 0.1,
        type: 'spring',
        stiffness: 300,
        damping: 24,
      }}
      whileHover={{ x: 4 }}
      onClick={() => isComplete && navigate(`/interaction/${pair.id}`)}
      className={`flex items-center justify-between rounded-xl border p-5 transition-all ${
        isComplete
          ? 'border-border-subtle bg-bg-card hover:bg-bg-card-hover cursor-pointer'
          : 'border-border-subtle/50 bg-bg-card/50'
      }`}
      style={isComplete && isHighScore ? { borderLeftWidth: 3, borderLeftColor: 'var(--color-score-high)' } : undefined}
    >
      <div className="flex items-center gap-4 flex-1 min-w-0">
        <div className="flex items-center gap-3 min-w-0">
          <div className="px-3 py-1.5 rounded-lg bg-accent-purple/10 border border-accent-purple/20">
            <span className="text-accent-purple font-mono text-sm font-bold">{protein.name}</span>
          </div>
          <ArrowRight size={14} className="text-slate-600 shrink-0" />
          <div className="px-3 py-1.5 rounded-lg bg-accent-blue/10 border border-accent-blue/20">
            <span className="text-accent-blue font-mono text-sm font-bold">{ligand.name}</span>
          </div>
        </div>
      </div>

      <div className="flex items-center gap-4">
        {isComplete ? (
          <>
            <motion.div
              initial={{ scale: 0 }}
              animate={{ scale: [0, 1.2, 1] }}
              transition={{ type: 'spring', stiffness: 500, damping: 15, delay: index * 0.1 + 0.2 }}
              className="px-3 py-1 rounded-full text-sm font-bold"
              style={{
                color: getScoreColor(pair.score),
                backgroundColor: `${getScoreColor(pair.score)}15`,
              }}
            >
              {pair.score}
            </motion.div>
            <CheckCircle2 size={16} className="text-cyan-glow" />
          </>
        ) : (
          <Loader2 size={16} className="text-accent-blue animate-spin" />
        )}
      </div>
    </motion.div>
  );
}
