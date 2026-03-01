import { motion } from "framer-motion";
import { Bot, Loader2, CheckCircle2, XCircle, AlertTriangle } from "lucide-react";
import type { Agent } from "../../types";

interface AgentSidebarProps {
  agents: Agent[];
  activeId: string | null;
  onChange: (id: string) => void;
  loading?: boolean;
  emptyText?: string;
}

const statusIcon: Record<string, typeof CheckCircle2> = {
  completed: CheckCircle2,
  failed: XCircle,
  max_turns: AlertTriangle,
  running: Loader2,
};

const statusColor: Record<string, string> = {
  completed: "text-emerald-500",
  failed: "text-red-500",
  max_turns: "text-amber-500",
  running: "text-teal-500",
};

export default function AgentSidebar({ agents, activeId, onChange, loading, emptyText = "No agents yet" }: AgentSidebarProps) {
  return (
    <aside className="w-64 shrink-0 sticky top-20 self-start border-r border-slate-200 bg-slate-50/50 rounded-l-xl pr-0">
      <div className="p-4">
        <h3 className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-3 px-3">
          Agents
        </h3>
        {loading && agents.length === 0 ? (
          <div className="flex items-center justify-center py-8 text-slate-400">
            <Loader2 className="w-5 h-5 animate-spin" />
          </div>
        ) : agents.length === 0 ? (
          <p className="px-3 text-sm text-slate-400">{emptyText}</p>
        ) : (
          <nav className="space-y-1">
            {agents.map((agent) => {
              const isActive = agent.agentId === activeId;
              const Icon = statusIcon[agent.status] || Bot;
              const color = statusColor[agent.status] || "text-slate-400";
              return (
                <button
                  key={agent.agentId}
                  onClick={() => onChange(agent.agentId)}
                  className={`relative w-full text-left px-3 py-3 rounded-lg transition-colors ${
                    isActive
                      ? "bg-teal-50 text-teal-700"
                      : "text-slate-600 hover:text-slate-900 hover:bg-slate-100"
                  }`}
                >
                  {isActive && (
                    <motion.div
                      layoutId="sidebar-active"
                      className="absolute left-0 top-1 bottom-1 w-1 rounded-full bg-teal-500"
                      transition={{ type: "spring", stiffness: 350, damping: 30 }}
                    />
                  )}
                  <div className="flex items-center gap-2.5">
                    <Icon
                      className={`w-4 h-4 shrink-0 ${isActive ? "text-teal-600" : color} ${
                        agent.status === "running" ? "animate-spin" : ""
                      }`}
                    />
                    <div className="min-w-0 flex-1">
                      <p className={`text-sm font-medium truncate ${isActive ? "text-teal-700" : ""}`}>
                        {agent.task || agent.agentId}
                      </p>
                      <p className="text-xs text-slate-400 truncate">
                        {agent.status} &middot; {agent.totalTurns} turns
                        {agent.childCount > 0 && ` &middot; ${agent.childCount} sub`}
                      </p>
                    </div>
                  </div>
                </button>
              );
            })}
          </nav>
        )}
      </div>
    </aside>
  );
}
