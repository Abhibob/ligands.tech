import { motion, AnimatePresence } from 'framer-motion';
import { CheckCircle2, Loader2, Microscope, FlaskConical, Dna, Scan, TestTubes } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { getPairsForAgent } from '../data/mockData';
import CircularProgress from './CircularProgress';

const agentIcons = [Microscope, FlaskConical, Dna, Scan, TestTubes];

const taskTexts = [
  ['Docking EGFR + Erlotinib...', 'Analyzing HER2 binding...', 'Scoring BRAF affinity...'],
  ['Testing KRAS mutations...', 'Probing VEGFR sites...', 'Evaluating ALK pocket...'],
  ['Profiling CDK4 selectivity...', 'Checking TP53 fit...', 'Scanning EGFR variants...'],
  ['Validating cross-targets...', 'Testing HER2 + Erlotinib...', 'Scoring KRAS + Imatinib...'],
  ['Checking off-targets...', 'Analyzing ALK + Palbociclib...', 'Scanning TP53 surface...'],
];

// Varied card treatments by index
const cardVariants = [
  'accent-top rounded-xl bg-bg-card',                                    // gradient top accent
  'accent-left rounded-xl border border-border-subtle bg-bg-card',       // left accent bar
  'rounded-xl bg-gradient-to-br from-bg-card to-[#1a2540] border border-border-subtle', // subtle gradient bg
  'accent-top rounded-xl bg-bg-card',                                    // gradient top accent
  'card-inset rounded-xl bg-bg-card',                                    // inset shadow
];

export default function AgentCard({ agent, isComplete, progress, justCompleted, index = 0 }) {
  const navigate = useNavigate();
  const pairs = getPairsForAgent(agent.id);
  const IconComponent = agentIcons[index % agentIcons.length];
  const avgScore = Math.round(pairs.reduce((s, p) => s + p.score, 0) / pairs.length);

  // Cycle through task texts while running
  const taskIdx = Math.floor((progress / 100) * taskTexts[index % taskTexts.length].length);
  const currentTask = taskTexts[index % taskTexts.length][
    Math.min(taskIdx, taskTexts[index % taskTexts.length].length - 1)
  ];

  const treatment = cardVariants[index % cardVariants.length];

  return (
    <motion.div
      initial={{ opacity: 0, y: 16, scale: 0.97 }}
      animate={{
        opacity: 1,
        y: 0,
        scale: justCompleted ? 1.03 : 1,
      }}
      transition={{
        opacity: { duration: 0.4 },
        y: { type: 'spring', stiffness: 300, damping: 24 },
        scale: justCompleted
          ? { type: 'spring', stiffness: 500, damping: 15 }
          : { duration: 0.3 },
      }}
      whileHover={{ y: -2, scale: 1.01, transition: { type: 'spring', stiffness: 400, damping: 20 } }}
      onClick={() => navigate(`/agents/${agent.id}`)}
      className={`relative overflow-hidden p-6 cursor-pointer transition-colors duration-300 ${treatment} ${
        isComplete ? 'glow-cyan' : 'hover:bg-bg-card-hover'
      }`}
    >
      {/* Shimmer overlay on just completed */}
      {justCompleted && <div className="absolute inset-0 shimmer pointer-events-none" />}

      <div className="flex items-start justify-between mb-4">
        <div className="flex items-center gap-3">
          <div className={`w-10 h-10 rounded-lg flex items-center justify-center transition-colors ${
            isComplete ? 'bg-cyan-glow/15' : 'bg-white/5'
          }`}>
            <IconComponent size={20} className={isComplete ? 'text-cyan-glow' : 'text-slate-400'} />
          </div>
          <div>
            <h3 className="text-white font-semibold">{agent.name}</h3>
            <p className="text-slate-500 text-xs mt-0.5">{agent.specialty}</p>
          </div>
        </div>

        <AnimatePresence mode="wait">
          {isComplete ? (
            <motion.div
              key="check"
              initial={{ scale: 0, rotate: -45 }}
              animate={{ scale: 1, rotate: 0 }}
              transition={{ type: 'spring', stiffness: 500, damping: 15 }}
            >
              <CheckCircle2 size={20} className="text-cyan-glow" />
            </motion.div>
          ) : (
            <motion.div key="spin" exit={{ opacity: 0, scale: 0.5 }}>
              <Loader2 size={20} className="text-accent-blue animate-spin" />
            </motion.div>
          )}
        </AnimatePresence>
      </div>

      {/* Status text */}
      <AnimatePresence mode="wait">
        {isComplete ? (
          <motion.div
            key="done"
            initial={{ opacity: 0, y: 4 }}
            animate={{ opacity: 1, y: 0 }}
            className="text-sm text-cyan-glow mb-3 font-medium"
          >
            Complete — {pairs.length} pairs scored
          </motion.div>
        ) : (
          <motion.div
            key="running"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="text-sm text-slate-500 mb-3 font-mono truncate"
          >
            {currentTask}
          </motion.div>
        )}
      </AnimatePresence>

      {/* Circular progress ring */}
      <div className="flex items-center justify-between">
        <CircularProgress
          value={progress}
          size={48}
          strokeWidth={3.5}
          color={isComplete ? 'var(--color-cyan-glow)' : 'var(--color-accent-blue)'}
        />
        <div className="text-right">
          <p className="text-xs text-slate-500">
            {pairs.length} pair{pairs.length !== 1 ? 's' : ''}
          </p>
          {isComplete && (
            <motion.p
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              className="text-xs text-slate-400 mt-0.5"
            >
              avg <span className="text-cyan-glow font-mono">{avgScore}</span>
            </motion.p>
          )}
        </div>
      </div>
    </motion.div>
  );
}
