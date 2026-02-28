import { motion } from "framer-motion";
import { FlaskConical } from "lucide-react";
import { researchers } from "../../data";

interface ResearcherSidebarProps {
  activeId: string;
  onChange: (id: string) => void;
}

export default function ResearcherSidebar({ activeId, onChange }: ResearcherSidebarProps) {
  return (
    <aside className="w-64 shrink-0 sticky top-20 self-start border-r border-slate-200 bg-slate-50/50 rounded-l-xl pr-0">
      <div className="p-4">
        <h3 className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-3 px-3">
          Researchers
        </h3>
        <nav className="space-y-1">
          {researchers.map((r) => {
            const isActive = r.id === activeId;
            return (
              <button
                key={r.id}
                onClick={() => onChange(r.id)}
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
                  <FlaskConical className={`w-4 h-4 shrink-0 ${isActive ? "text-teal-600" : "text-slate-400"}`} />
                  <div className="min-w-0">
                    <p className={`text-sm font-medium truncate ${isActive ? "text-teal-700" : ""}`}>
                      {r.name}
                    </p>
                    <p className="text-xs text-slate-400 truncate">{r.specialty}</p>
                  </div>
                </div>
              </button>
            );
          })}
        </nav>
      </div>
    </aside>
  );
}
