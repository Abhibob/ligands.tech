import { useEffect, useRef } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  X,
  Terminal,
  FileText,
  FolderOpen,
  Brain,
  CheckSquare,
  Zap,
  AlertTriangle,
  Play,
  Wifi,
  WifiOff,
} from "lucide-react";
import type { AgentEvent } from "../../hooks/useAgentEvents";
import MarkdownDark from "../shared/MarkdownDark";

interface Props {
  open: boolean;
  onClose: () => void;
  events: AgentEvent[];
  connected: boolean;
  agentId: string | null;
}

function EventIcon({ type, tool }: { type: string; tool?: string }) {
  const cls = "w-4 h-4 flex-shrink-0";
  if (type === "tool_call") {
    switch (tool) {
      case "command":
        return <Terminal className={`${cls} text-amber-500`} />;
      case "read_file":
        return <FileText className={`${cls} text-blue-500`} />;
      case "list_files":
        return <FolderOpen className={`${cls} text-purple-500`} />;
      case "think":
        return <Brain className={`${cls} text-indigo-500`} />;
      case "checklist":
        return <CheckSquare className={`${cls} text-emerald-500`} />;
      case "spawn_subagent":
      case "check_subagent":
        return <Zap className={`${cls} text-cyan-500`} />;
      default:
        return <Play className={`${cls} text-slate-400`} />;
    }
  }
  if (type === "tool_result") return <Play className={`${cls} text-green-500`} />;
  if (type === "thinking") return <Brain className={`${cls} text-violet-400`} />;
  if (type === "nudge") return <AlertTriangle className={`${cls} text-yellow-500`} />;
  if (type === "assistant_text") return <Brain className={`${cls} text-indigo-400`} />;
  if (type === "turn_start") return <Play className={`${cls} text-slate-300`} />;
  if (type === "done") return <CheckSquare className={`${cls} text-teal-500`} />;
  return <Play className={`${cls} text-slate-400`} />;
}

function formatTime(ts: number) {
  const d = new Date(ts * 1000);
  return d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" });
}

function EventEntry({ event }: { event: AgentEvent }) {
  const { type, data } = event;

  if (type === "turn_start") {
    return (
      <div className="flex items-center gap-2 py-1.5 px-3 text-xs text-slate-400 border-t border-slate-800/50">
        <EventIcon type={type} />
        <span className="font-mono">
          Turn {String(data.turn)}/{String(data.maxTurns)}
        </span>
        <span className="ml-auto text-slate-500">{formatTime(event.timestamp)}</span>
      </div>
    );
  }

  if (type === "tool_call") {
    const tool = data.tool as string;
    const display = data.display as string;
    return (
      <div className="py-1.5 px-3 hover:bg-slate-800/50 transition-colors">
        <div className="flex items-start gap-2">
          <EventIcon type={type} tool={tool} />
          <div className="min-w-0 flex-1">
            <span className="text-xs font-semibold text-slate-300">{tool}</span>
            <p className="text-xs text-slate-400 font-mono break-all mt-0.5 leading-relaxed">
              {display}
            </p>
          </div>
        </div>
      </div>
    );
  }

  if (type === "tool_result") {
    const summary = data.summary as string;
    const elapsed = data.elapsed as number;
    return (
      <div className="py-1 px-3 pl-9">
        <span className="text-xs text-green-400/80 font-mono">
          {summary || "ok"}{elapsed ? ` (${elapsed}s)` : ""}
        </span>
      </div>
    );
  }

  if (type === "nudge") {
    return (
      <div className="py-1.5 px-3 bg-yellow-900/20 border-l-2 border-yellow-500">
        <div className="flex items-start gap-2">
          <EventIcon type={type} />
          <p className="text-xs text-yellow-400">
            Nudging agent to act ({String(data.count)}/3)
          </p>
        </div>
      </div>
    );
  }

  if (type === "thinking") {
    const thought = data.thought as string;
    return (
      <div className="py-1.5 px-3 bg-violet-900/15 border-l-2 border-violet-500/50">
        <div className="flex items-start gap-2">
          <EventIcon type={type} />
          <div className="min-w-0 flex-1">
            <span className="text-xs font-semibold text-violet-300">Thinking</span>
            <div className="text-violet-300/70 mt-0.5">
              <MarkdownDark>{thought}</MarkdownDark>
            </div>
          </div>
        </div>
      </div>
    );
  }

  if (type === "assistant_text") {
    const text = data.text as string;
    return (
      <div className="py-1.5 px-3 bg-indigo-900/10 border-l-2 border-indigo-500/50">
        <div className="flex items-start gap-2">
          <EventIcon type={type} />
          <div className="min-w-0 flex-1 text-indigo-300/80">
            <MarkdownDark>{text}</MarkdownDark>
          </div>
        </div>
      </div>
    );
  }

  if (type === "done") {
    const status = data.status as string;
    const turns = data.turns as number;
    return (
      <div className="py-2 px-3 bg-teal-900/20 border-l-2 border-teal-500">
        <div className="flex items-start gap-2">
          <EventIcon type={type} />
          <div className="text-xs">
            <span className="text-teal-400 font-semibold">
              Agent finished — {status}
            </span>
            <span className="text-teal-400/60 ml-1">({turns} turns)</span>
          </div>
        </div>
      </div>
    );
  }

  if (type === "agent_start") {
    return (
      <div className="py-2 px-3 bg-slate-800/50 border-l-2 border-slate-500">
        <div className="flex items-start gap-2">
          <Play className="w-4 h-4 text-teal-500 flex-shrink-0" />
          <p className="text-xs text-slate-300">
            Agent started: <span className="text-slate-400 italic">{(data.task as string)?.slice(0, 200)}</span>
          </p>
        </div>
      </div>
    );
  }

  return null;
}

export default function ThinkingSidebar({ open, onClose, events, connected, agentId }: Props) {
  const scrollRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom on new events
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [events.length]);

  return (
    <AnimatePresence>
      {open && (
        <>
          {/* Backdrop */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.2 }}
            className="fixed inset-0 z-40 bg-black/40 backdrop-blur-sm"
            onClick={onClose}
          />

          {/* Sidebar */}
          <motion.div
            initial={{ x: "100%" }}
            animate={{ x: 0 }}
            exit={{ x: "100%" }}
            transition={{ type: "spring", damping: 30, stiffness: 300 }}
            className="fixed top-0 right-0 bottom-0 z-50 w-[480px] max-w-[90vw] bg-slate-900 border-l border-slate-700/50 shadow-2xl flex flex-col"
          >
            {/* Header */}
            <div className="flex items-center justify-between px-4 py-3 border-b border-slate-700/50 bg-slate-900/95">
              <div className="flex items-center gap-2">
                <Brain className="w-5 h-5 text-teal-500" />
                <h2 className="text-sm font-semibold text-slate-200">Agent Thinking</h2>
                {agentId && (
                  <span className="text-xs text-slate-500 font-mono">{agentId.slice(0, 16)}</span>
                )}
              </div>
              <div className="flex items-center gap-2">
                {/* Connection indicator */}
                <div className="flex items-center gap-1">
                  {connected ? (
                    <Wifi className="w-3.5 h-3.5 text-green-400" />
                  ) : (
                    <WifiOff className="w-3.5 h-3.5 text-slate-500" />
                  )}
                  <span className={`text-xs ${connected ? "text-green-400" : "text-slate-500"}`}>
                    {connected ? "Live" : "Disconnected"}
                  </span>
                </div>
                <button
                  onClick={onClose}
                  className="p-1.5 rounded-md hover:bg-slate-800 transition-colors"
                >
                  <X className="w-4 h-4 text-slate-400" />
                </button>
              </div>
            </div>

            {/* Event log */}
            <div ref={scrollRef} className="flex-1 overflow-y-auto">
              {events.length === 0 ? (
                <div className="flex flex-col items-center justify-center h-full text-slate-500">
                  <Brain className="w-8 h-8 mb-2 opacity-30" />
                  <p className="text-sm">
                    {connected ? "Waiting for agent events..." : "No events yet"}
                  </p>
                </div>
              ) : (
                <div className="py-1">
                  {events.map((event, i) => (
                    <EventEntry key={i} event={event} />
                  ))}
                </div>
              )}
            </div>

            {/* Footer with stats */}
            <div className="px-4 py-2 border-t border-slate-700/50 bg-slate-900/95 text-xs text-slate-500 flex items-center justify-between">
              <span>{events.length} events</span>
              {events.length > 0 && (
                <span>
                  {events.filter((e) => e.type === "tool_call").length} tool calls
                </span>
              )}
            </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
}
