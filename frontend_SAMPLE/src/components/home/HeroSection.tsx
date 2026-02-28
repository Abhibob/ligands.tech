import { Link } from "react-router-dom";
import { motion } from "framer-motion";
import { FlaskConical, Users, Atom, TestTubes, ArrowRight } from "lucide-react";

const stats = [
  { icon: Users, label: "Researchers", value: 5 },
  { icon: TestTubes, label: "Pairs", value: 17 },
  { icon: Atom, label: "Proteins", value: 8 },
  { icon: FlaskConical, label: "Ligands", value: 8 },
];

function CountUp({ value }: { value: number }) {
  return (
    <motion.span
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5, ease: "easeOut" }}
    >
      {value}
    </motion.span>
  );
}

export default function HeroSection() {
  return (
    <div className="flex flex-col justify-center h-full py-16 lg:py-0">
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.6 }}
      >
        <h1 className="text-4xl lg:text-5xl font-bold text-slate-900 leading-tight">
          Protein-Ligand
          <br />
          <span className="text-gradient-shimmer">Compatibility Analysis</span>
        </h1>
        <p className="mt-4 text-lg text-slate-500 max-w-lg" style={{ fontFamily: "Inter, sans-serif" }}>
          Explore binding affinities, interaction profiles, and molecular compatibility
          scores across 5 researchers and 17 protein-ligand pairs.
        </p>
      </motion.div>

      <motion.div
        className="flex flex-wrap gap-3 mt-8"
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.6, delay: 0.2 }}
      >
        {stats.map((stat, i) => (
          <motion.div
            key={stat.label}
            className="flex items-center gap-2 px-4 py-2 rounded-full bg-slate-50 border border-slate-200 cursor-default"
            whileHover={{ scale: 1.05, borderColor: "#99f6e4" }}
            transition={{ type: "spring", stiffness: 400, damping: 20 }}
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            // eslint-disable-next-line @typescript-eslint/no-explicit-any
            {...({ transition: { duration: 0.4, delay: 0.3 + i * 0.08 } } as any)}
          >
            <stat.icon className="w-4 h-4 text-teal-600" />
            <span className="text-sm font-medium text-slate-700" style={{ fontFamily: "Inter, sans-serif" }}>
              <CountUp value={stat.value} /> {stat.label}
            </span>
          </motion.div>
        ))}
      </motion.div>

      <motion.div
        className="mt-8"
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.6, delay: 0.4 }}
      >
        <Link to="/researchers">
          <motion.span
            className="inline-flex items-center gap-2 px-6 py-3 rounded-lg bg-teal-600 text-white font-medium hover:bg-teal-700 transition-colors animate-pulse-subtle"
            whileHover="hover"
          >
            Start Analysis
            <motion.span
              variants={{ hover: { x: 4 } }}
              transition={{ type: "spring", stiffness: 400, damping: 20 }}
            >
              <ArrowRight className="w-4 h-4" />
            </motion.span>
          </motion.span>
        </Link>
      </motion.div>

      {/* Floating decorative molecular formulas */}
      <div className="absolute top-20 right-10 text-slate-200/40 text-sm font-mono pointer-events-none select-none hidden lg:block">
        <motion.div
          animate={{ y: [0, -8, 0] }}
          transition={{ duration: 5, repeat: Infinity, ease: "easeInOut" }}
        >
          C₂₁H₂₅ClFN₃O₅
        </motion.div>
      </div>
      <div className="absolute bottom-32 left-8 text-slate-200/30 text-xs font-mono pointer-events-none select-none hidden lg:block">
        <motion.div
          animate={{ y: [0, 6, 0] }}
          transition={{ duration: 7, repeat: Infinity, ease: "easeInOut", delay: 1 }}
        >
          H₂N-CH(R)-COOH
        </motion.div>
      </div>
    </div>
  );
}
