import { motion, AnimatePresence } from 'framer-motion';
import { CheckCircle2, Loader2, Microscope, FlaskConical, Dna, Scan, TestTubes } from 'lucide-react';
import CircularProgress from './CircularProgress';
import { getPairsForAgent } from '../data/mockData';

const agentIcons = [Microscope, FlaskConical, Dna, Scan, TestTubes];

const taskTexts = [
  ['Docking EGFR + Erlotinib...', 'Analyzing HER2 binding...', 'Scoring BRAF affinity...'],
  ['Testing KRAS mutations...', 'Probing VEGFR sites...', 'Evaluating ALK pocket...'],
  ['Profiling CDK4 selectivity...', 'Checking TP53 fit...', 'Scanning EGFR variants...'],
  ['Validating cross-targets...', 'Testing HER2 + Erlotinib...', 'Scoring KRAS + Imatinib...'],
  ['Checking off-targets...', 'Analyzing ALK + Palbociclib...', 'Scanning TP53 surface...'],
];

export default function AgentSidebarItem({ agent, isComplete, progress, isSelected, onClick, index = 0 }) {
  const pairs = getPairsForAgent(agent.id);
  const IconComponent = agentIcons[index % agentIcons.length];

  const taskIdx = Math.floor((progress / 100) * taskTexts[index % taskTexts.length].length);
  const currentTask = taskTexts[index % taskTexts.length][
    Math.min(taskIdx, taskTexts[index % taskTexts.length].length - 1)
  ];

  return (
    <motion.div
      onClick={onClick}
      whileHover={{ x: 2 }}
      className={`relative flex items-center gap-3 px-4 py-3 cursor-pointer rounded-lg transition-colors ${
        isSelected
          ? 'bg-white/[0.06] border-l-[3px] border-l-cyan-glow'
          : 'border-l-[3px] border-l-transparent hover:bg-white/[0.03]'
      }`}
    >
      {/* Icon */}
      <div className={`w-8 h-8 rounded-lg flex items-center justify-center shrink-0 ${
        isComplete ? 'bg-cyan-glow/15' : 'bg-white/5'
      }`}>
        <IconComponent size={16} className={isComplete ? 'text-cyan-glow' : 'text-slate-400'} />
      </div>

      {/* Name + status */}
      <div className="flex-1 min-w-0">
        <p className="text-sm font-medium text-white truncate">{agent.name}</p>
        <AnimatePresence mode="wait">
          {isComplete ? (
            <motion.p
              key="done"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              className="text-[11px] text-cyan-glow truncate"
            >
              Complete — {pairs.length} pairs
            </motion.p>
          ) : (
            <motion.p
              key="task"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="text-[11px] text-slate-500 font-mono truncate"
            >
              {currentTask}
            </motion.p>
          )}
        </AnimatePresence>
      </div>

      {/* Progress ring or check */}
      <div className="shrink-0">
        <AnimatePresence mode="wait">
          {isComplete ? (
            <motion.div
              key="check"
              initial={{ scale: 0 }}
              animate={{ scale: 1 }}
              transition={{ type: 'spring', stiffness: 500, damping: 15 }}
            >
              <CheckCircle2 size={18} className="text-cyan-glow" />
            </motion.div>
          ) : (
            <motion.div key="ring" exit={{ opacity: 0, scale: 0.5 }}>
              <CircularProgress
                value={progress}
                size={36}
                strokeWidth={2.5}
                color="var(--color-accent-blue)"
              />
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </motion.div>
  );
}
