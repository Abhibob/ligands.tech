import { motion } from "framer-motion";
import PairCard from "./PairCard";
import type { Pair } from "../../types";

interface PairCardGridProps {
  pairs: Pair[];
}

const container = {
  hidden: { opacity: 0 },
  show: {
    opacity: 1,
    transition: {
      staggerChildren: 0.08,
    },
  },
};

const item = {
  hidden: { opacity: 0, y: 20 },
  show: { opacity: 1, y: 0, transition: { duration: 0.4, ease: "easeOut" as const } },
};

export default function PairCardGrid({ pairs }: PairCardGridProps) {
  return (
    <motion.div
      className="grid grid-cols-1 lg:grid-cols-2 xl:grid-cols-3 gap-5"
      variants={container}
      initial="hidden"
      animate="show"
    >
      {pairs.map((pair) => (
        <motion.div key={pair.id} variants={item}>
          <PairCard pair={pair} />
        </motion.div>
      ))}
    </motion.div>
  );
}
