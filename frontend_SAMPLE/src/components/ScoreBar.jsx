import { motion } from 'framer-motion';
import { getScoreColor } from '../data/mockData';

export default function ScoreBar({ score, height = 8, showLabel = false }) {
  const color = getScoreColor(score);

  return (
    <div className="flex items-center gap-3 w-full">
      <div
        className="relative flex-1 rounded-full overflow-hidden"
        style={{ height, backgroundColor: 'rgba(255,255,255,0.05)' }}
      >
        {/* Tick marks at 25, 50, 75 */}
        {[25, 50, 75].map(tick => (
          <div
            key={tick}
            className="absolute top-0 bottom-0 w-px bg-white/[0.08]"
            style={{ left: `${tick}%` }}
          />
        ))}
        {/* Gradient fill */}
        <motion.div
          className="h-full rounded-full relative"
          initial={{ width: 0 }}
          animate={{ width: `${score}%` }}
          transition={{ duration: 1, ease: 'easeOut', delay: 0.2 }}
          style={{
            background: `linear-gradient(90deg, ${color}88, ${color})`,
          }}
        >
          {/* Notch indicator at endpoint */}
          <div
            className="absolute right-0 top-1/2 -translate-y-1/2 w-0.5 rounded-full"
            style={{
              height: height + 4,
              backgroundColor: color,
            }}
          />
        </motion.div>
      </div>
      {showLabel && (
        <span className="text-sm font-bold font-mono w-8 text-right" style={{ color }}>
          {score}
        </span>
      )}
    </div>
  );
}
