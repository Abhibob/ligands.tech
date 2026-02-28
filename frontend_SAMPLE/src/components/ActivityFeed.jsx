import { useEffect, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';

export default function ActivityFeed({ entries }) {
  const scrollRef = useRef(null);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [entries.length]);

  return (
    <div
      ref={scrollRef}
      className="rounded-lg bg-[#0d1117] border-l-2 border-cyan-glow/40 overflow-y-auto"
      style={{ maxHeight: 180, minHeight: 80 }}
    >
      <div className="p-4 font-mono text-xs leading-relaxed">
        <AnimatePresence initial={false}>
          {entries.map((entry, i) => (
            <motion.div
              key={i}
              initial={{ opacity: 0, x: -8 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ type: 'spring', stiffness: 400, damping: 25 }}
              className="py-0.5"
            >
              <span className="text-slate-600">[{entry.timestamp}]</span>{' '}
              <span style={{ color: entry.color || '#06d6a0' }}>{entry.message}</span>
            </motion.div>
          ))}
        </AnimatePresence>
        {entries.length === 0 && (
          <span className="text-slate-600">Waiting for agent activity...</span>
        )}
      </div>
    </div>
  );
}
