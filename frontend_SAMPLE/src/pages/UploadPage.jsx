import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import { Play, Dna, FlaskConical, Users, Layers } from 'lucide-react';
import FileUpload from '../components/FileUpload';
import { slideFromLeft, scaleIn } from '../lib/animations';

export default function UploadPage() {
  const [file, setFile] = useState(null);
  const navigate = useNavigate();

  const handleStart = () => {
    if (file) navigate('/agents');
  };

  return (
    <div className="min-h-[calc(100vh-4rem)] flex items-center justify-center px-6 py-16 relative overflow-hidden">
      {/* Decorative SVG behind left column */}
      <svg
        className="absolute left-[-80px] top-1/2 -translate-y-1/2 opacity-[0.04] pointer-events-none"
        width="500"
        height="600"
        viewBox="0 0 500 600"
        fill="none"
      >
        <path
          d="M250 50 C350 120, 400 200, 350 300 C300 400, 200 420, 150 350 C100 280, 80 180, 150 120 C200 80, 300 60, 350 150"
          stroke="var(--color-cyan-glow)"
          strokeWidth="1.5"
          fill="none"
        />
        <path
          d="M200 100 C280 160, 320 250, 280 350 C240 450, 160 460, 120 380 C80 300, 60 200, 120 140 C160 100, 240 90, 300 170"
          stroke="var(--color-accent-purple)"
          strokeWidth="1"
          fill="none"
        />
        <circle cx="250" cy="300" r="60" stroke="var(--color-accent-blue)" strokeWidth="0.8" fill="none" strokeDasharray="4 6" />
        <circle cx="200" cy="250" r="30" stroke="var(--color-cyan-glow)" strokeWidth="0.5" fill="none" />
      </svg>

      <div className="max-w-5xl w-full grid grid-cols-1 lg:grid-cols-2 gap-16 items-center relative z-10">
        {/* Left column — text, heading, button, stats */}
        <motion.div
          variants={slideFromLeft}
          initial="hidden"
          animate="show"
        >
          <div className="flex items-center gap-3 mb-6">
            <Dna size={28} className="text-accent-purple" />
            <span className="text-slate-600 text-xl">/</span>
            <FlaskConical size={28} className="text-accent-blue" />
          </div>

          <h1 className="text-5xl lg:text-6xl font-bold text-white mb-4 leading-tight">
            Protein-Ligand{' '}
            <span className="text-gradient">Compatibility</span>{' '}
            Analysis
          </h1>

          <p className="text-slate-400 text-lg mb-8 max-w-md">
            Upload a document containing protein and ligand targets. Our subagent
            network will analyze binding interactions and rank compatibility.
          </p>

          {/* Stats badges */}
          <div className="flex flex-wrap gap-2 mb-8">
            <span className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-accent-purple/10 border border-accent-purple/20 text-accent-purple text-xs font-medium">
              <Users size={12} />
              5 Subagents
            </span>
            <span className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-accent-blue/10 border border-accent-blue/20 text-accent-blue text-xs font-medium">
              <Layers size={12} />
              17 Pairs
            </span>
            <span className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-cyan-glow/10 border border-cyan-glow/20 text-cyan-glow text-xs font-medium">
              <FlaskConical size={12} />
              Mock Engine
            </span>
          </div>

          <AnimatePresence>
            {file && (
              <motion.div
                initial={{ opacity: 0, x: -20 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: -10 }}
              >
                <button
                  onClick={handleStart}
                  className="group relative flex items-center gap-3 px-8 py-4 rounded-xl bg-cyan-glow/10 border border-cyan-glow/40 text-cyan-glow font-semibold text-lg cursor-pointer overflow-hidden transition-colors hover:text-white"
                >
                  <span className="absolute inset-0 bg-gradient-to-r from-cyan-glow/30 to-cyan-glow/10 translate-x-[-100%] group-hover:translate-x-0 transition-transform duration-500" />
                  <Play size={20} className="relative z-10" />
                  <span className="relative z-10">Start Analysis</span>
                </button>
              </motion.div>
            )}
          </AnimatePresence>
        </motion.div>

        {/* Right column — upload zone */}
        <motion.div
          variants={scaleIn}
          initial="hidden"
          animate="show"
          transition={{ delay: 0.15 }}
        >
          <FileUpload onFileSelect={setFile} />
        </motion.div>
      </div>
    </div>
  );
}
