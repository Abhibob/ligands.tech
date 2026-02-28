import { useState, useEffect, useRef, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import { Eye, Microscope, FlaskConical, Dna, Scan, TestTubes } from 'lucide-react';
import AgentSidebarItem from '../components/AgentSidebarItem';
import PairPreviewCard from '../components/PairPreviewCard';
import StepIndicator from '../components/StepIndicator';
import ActivityFeed from '../components/ActivityFeed';
import { agents, getPairsForAgent } from '../data/mockData';
import { stagger } from '../lib/animations';

const agentIcons = [Microscope, FlaskConical, Dna, Scan, TestTubes];

function formatTime(d) {
  return [d.getHours(), d.getMinutes(), d.getSeconds()]
    .map(n => String(n).padStart(2, '0'))
    .join(':');
}

export default function AgentsPage() {
  const { id } = useParams();
  const navigate = useNavigate();

  // Auto-select first agent if none specified
  const selectedId = id || agents[0].id;
  const selectedAgent = agents.find(a => a.id === selectedId);
  const selectedIndex = agents.findIndex(a => a.id === selectedId);
  const selectedPairs = getPairsForAgent(selectedId);
  const IconComponent = agentIcons[selectedIndex >= 0 ? selectedIndex % agentIcons.length : 0];

  // ── Agent progress simulation (migrated from AgentsDashboard) ──
  const [agentStates, setAgentStates] = useState(
    agents.map(a => ({ id: a.id, complete: false, progress: 0, justCompleted: false }))
  );
  const [feedEntries, setFeedEntries] = useState([]);
  const justCompletedTimers = useRef({});
  const completedRef = useRef(new Set());

  const addFeedEntry = useCallback((message, color) => {
    setFeedEntries(prev => [...prev, { timestamp: formatTime(new Date()), message, color }]);
  }, []);

  useEffect(() => {
    const intervals = agents.map((agent, idx) => {
      const duration = agent.delay;
      const stepMs = 50;
      const totalSteps = duration / stepMs;
      let step = 0;

      return setInterval(() => {
        step++;
        const progress = Math.min((step / totalSteps) * 100, 100);
        const complete = progress >= 100;

        setAgentStates(prev =>
          prev.map(s =>
            s.id === agent.id ? { ...s, progress, complete } : s
          )
        );

        if (complete && !completedRef.current.has(agent.id)) {
          completedRef.current.add(agent.id);
          clearInterval(intervals[idx]);

          const pairs = getPairsForAgent(agent.id);
          const avg = Math.round(pairs.reduce((s, p) => s + p.score, 0) / pairs.length);

          setAgentStates(prev =>
            prev.map(s =>
              s.id === agent.id ? { ...s, justCompleted: true } : s
            )
          );
          addFeedEntry(
            `${agent.name} completed — ${pairs.length} pairs analyzed (avg score: ${avg})`,
            '#06d6a0'
          );

          justCompletedTimers.current[agent.id] = setTimeout(() => {
            setAgentStates(prev =>
              prev.map(s =>
                s.id === agent.id ? { ...s, justCompleted: false } : s
              )
            );
          }, 3000);
        }
      }, stepMs);
    });

    return () => {
      intervals.forEach(clearInterval);
      Object.values(justCompletedTimers.current).forEach(clearTimeout);
    };
  }, [addFeedEntry]);

  const completedCount = agentStates.filter(a => a.complete).length;
  const allDone = completedCount === agents.length;

  // Final log line
  useEffect(() => {
    if (allDone && feedEntries.length > 0 && !feedEntries.some(e => e.message.includes('All agents'))) {
      addFeedEntry('All agents complete — results ready for review', '#3b82f6');
    }
  }, [allDone, feedEntries, addFeedEntry]);

  // ── Pair completion simulation (migrated from AgentDetail) ──
  const [completedPairs, setCompletedPairs] = useState(new Set());

  useEffect(() => {
    setCompletedPairs(new Set());
    const timers = selectedPairs.map((pair, i) => {
      return setTimeout(() => {
        setCompletedPairs(prev => new Set([...prev, pair.id]));
      }, 800 + i * 600);
    });
    return () => timers.forEach(clearTimeout);
  }, [selectedId]);

  const pairsAllDone = completedPairs.size === selectedPairs.length;

  // ── Step indicator ──
  const steps = agents.map((agent, i) => ({
    label: agent.name.split(' ')[1],
    complete: agentStates[i].complete,
  }));

  // ── Selected agent state ──
  const selectedState = agentStates.find(s => s.id === selectedId);

  return (
    <div className="flex flex-col h-[calc(100vh-4rem)]">
      {/* ── Header ── */}
      <div className="px-6 py-4 border-b border-border-subtle/50">
        <div className="flex items-center justify-between mb-3">
          <div>
            <h1 className="text-xl font-bold text-white">Subagent Network</h1>
            <p className="text-sm text-slate-400">
              {allDone ? (
                'All agents have completed analysis.'
              ) : (
                <>
                  <motion.span
                    key={completedCount}
                    initial={{ opacity: 0, y: -8 }}
                    animate={{ opacity: 1, y: 0 }}
                    className="inline-block text-white font-semibold"
                  >
                    {completedCount}
                  </motion.span>
                  {' '}of {agents.length} agents complete
                </>
              )}
            </p>
          </div>
        </div>
        <StepIndicator steps={steps} />
      </div>

      {/* ── Body: Sidebar + Detail ── */}
      <div className="flex flex-1 overflow-hidden">
        {/* ── Sidebar ── */}
        <div className="w-80 border-r border-border-subtle/50 flex flex-col">
          {/* Agent list */}
          <div className="flex-1 overflow-y-auto py-3 px-2 space-y-1">
            {agents.map((agent, i) => {
              const state = agentStates.find(s => s.id === agent.id);
              return (
                <AgentSidebarItem
                  key={agent.id}
                  agent={agent}
                  isComplete={state.complete}
                  progress={state.progress}
                  isSelected={agent.id === selectedId}
                  onClick={() => navigate(`/agents/${agent.id}`, { replace: true })}
                  index={i}
                />
              );
            })}
          </div>

          {/* Activity feed */}
          <div className="border-t border-border-subtle/50 px-3 py-3">
            <p className="text-[10px] text-slate-500 uppercase tracking-wider font-medium mb-2">Activity</p>
            <ActivityFeed entries={feedEntries} />
          </div>

          {/* View Results button */}
          <AnimatePresence>
            {allDone && (
              <motion.div
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ type: 'spring', stiffness: 400, damping: 18 }}
                className="px-3 pb-4"
              >
                <button
                  onClick={() => navigate('/results')}
                  className="group relative w-full flex items-center justify-center gap-2 px-4 py-3 rounded-xl bg-cyan-glow/10 border border-cyan-glow/40 text-cyan-glow font-semibold text-sm cursor-pointer overflow-hidden transition-colors hover:text-white"
                >
                  <span className="absolute inset-0 bg-gradient-to-r from-cyan-glow/0 via-cyan-glow/20 to-cyan-glow/0 translate-x-[-100%] group-hover:translate-x-[100%] transition-transform duration-700" />
                  <Eye size={16} className="relative z-10" />
                  <span className="relative z-10">View Results</span>
                </button>
              </motion.div>
            )}
          </AnimatePresence>
        </div>

        {/* ── Detail Panel ── */}
        <div className="flex-1 overflow-y-auto">
          {selectedAgent ? (
            <div className="p-6">
              {/* Agent header */}
              <motion.div
                key={selectedId}
                initial={{ opacity: 0, x: 20 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ type: 'spring', stiffness: 300, damping: 24 }}
                className="flex items-center gap-4 mb-6"
              >
                <div className={`w-11 h-11 rounded-xl flex items-center justify-center transition-colors ${
                  pairsAllDone ? 'bg-cyan-glow/15 border border-cyan-glow/30' : 'bg-white/5 border border-border-subtle'
                }`}>
                  <IconComponent size={22} className={pairsAllDone ? 'text-cyan-glow' : 'text-slate-400'} />
                </div>
                <div>
                  <h2 className="text-lg font-bold text-white">{selectedAgent.name}</h2>
                  <p className="text-slate-400 text-sm">{selectedAgent.specialty}</p>
                </div>
                <motion.div
                  className={`ml-auto px-3 py-1.5 rounded-full text-xs font-medium ${
                    pairsAllDone
                      ? 'bg-cyan-glow/10 text-cyan-glow border border-cyan-glow/30'
                      : 'bg-accent-blue/10 text-accent-blue border border-accent-blue/30'
                  }`}
                  key={pairsAllDone ? 'done' : 'progress'}
                  initial={{ scale: 0.9, opacity: 0 }}
                  animate={{ scale: 1, opacity: 1 }}
                  transition={{ type: 'spring', stiffness: 400, damping: 20 }}
                >
                  {pairsAllDone ? 'Complete' : `Testing ${completedPairs.size}/${selectedPairs.length}`}
                </motion.div>
              </motion.div>

              {/* Pairs grid */}
              <motion.div
                key={selectedId + '-pairs'}
                variants={stagger.container}
                initial="hidden"
                animate="show"
                className="grid grid-cols-1 md:grid-cols-2 gap-4"
              >
                {selectedPairs.map((pair, i) => (
                  <motion.div key={pair.id} variants={stagger.item}>
                    <PairPreviewCard
                      pair={pair}
                      isComplete={completedPairs.has(pair.id)}
                      index={i}
                    />
                  </motion.div>
                ))}
              </motion.div>
            </div>
          ) : (
            <div className="flex items-center justify-center h-full text-slate-500">
              Select an agent to view its pairs.
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
