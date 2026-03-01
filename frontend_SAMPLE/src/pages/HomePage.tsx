import { Suspense, useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { motion } from "framer-motion";
import { Bot, TestTubes, Atom, FlaskConical, ArrowRight, Send } from "lucide-react";
import ProteinScene from "../components/home/ProteinScene";
import { api } from "../api/client";
import type { Stats } from "../types";

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

export default function HomePage() {
  const navigate = useNavigate();
  const [stats, setStats] = useState<Stats>({
    agentCount: 0,
    hypothesisCount: 0,
    proteinCount: 0,
    ligandCount: 0,
  });
  const [prompt, setPrompt] = useState("");
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    api.getStats().then(setStats).catch(() => {});
  }, []);

  const statItems = [
    { icon: Bot, label: "Agents", value: stats.agentCount },
    { icon: TestTubes, label: "Hypotheses", value: stats.hypothesisCount },
    { icon: Atom, label: "Proteins", value: stats.proteinCount },
    { icon: FlaskConical, label: "Ligands", value: stats.ligandCount },
  ];

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!prompt.trim() || submitting) return;
    setSubmitting(true);
    try {
      const res = await api.createRun(prompt.trim());
      navigate(`/agents/${res.agentId}`);
    } catch (err) {
      console.error("Failed to create run:", err);
      setSubmitting(false);
    }
  };

  return (
    <div className="max-w-7xl mx-auto px-6">
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 min-h-[calc(100vh-4rem)]">
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
            <p
              className="mt-4 text-lg text-slate-500 max-w-lg"
              style={{ fontFamily: "Inter, sans-serif" }}
            >
              AI-powered binding analysis with Boltz-2, GNINA, PoseBusters,
              and PLIP. Enter a prompt to start an agent run.
            </p>
          </motion.div>

          {/* Prompt input */}
          <motion.form
            onSubmit={handleSubmit}
            className="mt-8 max-w-lg"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, delay: 0.15 }}
          >
            <div className="relative">
              <textarea
                value={prompt}
                onChange={(e) => setPrompt(e.target.value)}
                placeholder="e.g. Analyze binding of erlotinib to EGFR..."
                rows={3}
                className="w-full px-4 py-3 pr-12 rounded-xl border border-slate-200 bg-white text-sm text-slate-900 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-teal-500 focus:border-transparent resize-none"
              />
              <button
                type="submit"
                disabled={!prompt.trim() || submitting}
                className="absolute right-3 bottom-3 p-2 rounded-lg bg-teal-600 text-white hover:bg-teal-700 transition-colors disabled:opacity-40"
              >
                <Send className="w-4 h-4" />
              </button>
            </div>
          </motion.form>

          {/* Stats */}
          <motion.div
            className="flex flex-wrap gap-3 mt-6"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, delay: 0.3 }}
          >
            {statItems.map((stat, i) => (
              <motion.div
                key={stat.label}
                className="flex items-center gap-2 px-4 py-2 rounded-full bg-slate-50 border border-slate-200 cursor-default"
                whileHover={{ scale: 1.05, borderColor: "#99f6e4" }}
                transition={{ type: "spring", stiffness: 400, damping: 20 }}
                initial={{ opacity: 0, y: 12 }}
                animate={{ opacity: 1, y: 0 }}
                // eslint-disable-next-line @typescript-eslint/no-explicit-any
                {...({ transition: { duration: 0.4, delay: 0.4 + i * 0.08 } } as any)}
              >
                <stat.icon className="w-4 h-4 text-teal-600" />
                <span
                  className="text-sm font-medium text-slate-700"
                  style={{ fontFamily: "Inter, sans-serif" }}
                >
                  <CountUp value={stat.value} /> {stat.label}
                </span>
              </motion.div>
            ))}
          </motion.div>

          <motion.div
            className="mt-6"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, delay: 0.5 }}
          >
            <button
              onClick={() => navigate("/agents")}
              className="inline-flex items-center gap-2 px-6 py-3 rounded-lg bg-teal-600 text-white font-medium hover:bg-teal-700 transition-colors"
            >
              View Agents
              <ArrowRight className="w-4 h-4" />
            </button>
          </motion.div>

          {/* Floating decorative molecular formulas */}
          <div className="absolute top-20 right-10 text-slate-200/40 text-sm font-mono pointer-events-none select-none hidden lg:block">
            <motion.div
              animate={{ y: [0, -8, 0] }}
              transition={{ duration: 5, repeat: Infinity, ease: "easeInOut" }}
            >
              C&#x2082;&#x2081;H&#x2082;&#x2085;ClFN&#x2083;O&#x2085;
            </motion.div>
          </div>
          <div className="absolute bottom-32 left-8 text-slate-200/30 text-xs font-mono pointer-events-none select-none hidden lg:block">
            <motion.div
              animate={{ y: [0, 6, 0] }}
              transition={{
                duration: 7,
                repeat: Infinity,
                ease: "easeInOut",
                delay: 1,
              }}
            >
              H&#x2082;N-CH(R)-COOH
            </motion.div>
          </div>
        </div>

        <div className="flex items-center justify-center min-h-[600px]">
          <Suspense
            fallback={
              <div className="w-full h-[600px] flex items-center justify-center text-slate-400">
                Loading 3D scene...
              </div>
            }
          >
            <ProteinScene />
          </Suspense>
        </div>
      </div>
    </div>
  );
}
