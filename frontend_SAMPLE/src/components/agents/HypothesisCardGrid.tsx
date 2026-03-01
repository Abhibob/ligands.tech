import { motion } from "framer-motion";
import HypothesisCard from "./HypothesisCard";
import type { Hypothesis } from "../../types";

interface HypothesisCardGridProps {
  hypotheses: Hypothesis[];
}

const container = {
  hidden: { opacity: 0 },
  show: {
    opacity: 1,
    transition: { staggerChildren: 0.08 },
  },
};

const item = {
  hidden: { opacity: 0, y: 20 },
  show: { opacity: 1, y: 0, transition: { duration: 0.4, ease: "easeOut" as const } },
};

export default function HypothesisCardGrid({ hypotheses }: HypothesisCardGridProps) {
  if (hypotheses.length === 0) {
    return (
      <p className="text-slate-400 text-sm py-8">No hypotheses for this agent yet.</p>
    );
  }

  return (
    <motion.div
      className="grid grid-cols-1 lg:grid-cols-2 xl:grid-cols-3 gap-5"
      variants={container}
      initial="hidden"
      animate="show"
    >
      {hypotheses.map((hyp) => (
        <motion.div key={hyp.id} variants={item}>
          <HypothesisCard hypothesis={hyp} />
        </motion.div>
      ))}
    </motion.div>
  );
}
