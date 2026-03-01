import { useState } from "react";
import { NavLink, useLocation, useNavigate } from "react-router-dom";
import { motion } from "framer-motion";
import { Plus } from "lucide-react";
import { api } from "../../api/client";

const links = [
  { to: "/", label: "Home" },
  { to: "/agents", label: "Agents" },
  { to: "/finished", label: "Finished" },
  { to: "/results", label: "Results" },
];

export default function Navbar() {
  const location = useLocation();
  const navigate = useNavigate();
  const [submitting, setSubmitting] = useState(false);

  const isActive = (to: string) => {
    if (to === "/") return location.pathname === "/";
    return location.pathname.startsWith(to);
  };

  const handleNewRun = async () => {
    const prompt = window.prompt("Enter a binding analysis prompt:");
    if (!prompt?.trim()) return;
    setSubmitting(true);
    try {
      const res = await api.createRun(prompt.trim());
      navigate(`/agents/${res.agentId}`);
    } catch (err) {
      console.error("Failed to create run:", err);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <nav className="fixed top-0 left-0 right-0 z-50 backdrop-blur-md bg-white/80 border-b border-slate-200/80">
      <div className="max-w-7xl mx-auto px-6 h-16 flex items-center justify-between">
        <NavLink to="/" className="flex items-center gap-1.5 text-xl font-semibold">
          <span className="relative flex h-2.5 w-2.5">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-teal-400 opacity-75" />
            <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-teal-500" />
          </span>
          <span className="text-slate-900">Ligands</span>
          <span className="text-teal-600">.tech</span>
        </NavLink>
        <div className="flex items-center gap-1 relative">
          {links.map((link) => {
            const active = isActive(link.to);
            return (
              <NavLink
                key={link.to}
                to={link.to}
                className={`relative px-4 py-2 text-sm font-medium rounded-lg transition-colors ${
                  active
                    ? "text-teal-600"
                    : "text-slate-600 hover:text-slate-900 hover:bg-slate-50"
                }`}
              >
                {link.label}
                {active && (
                  <motion.div
                    layoutId="nav-underline"
                    className="absolute bottom-0 left-2 right-2 h-0.5 bg-teal-500 rounded-full"
                    transition={{ type: "spring", stiffness: 380, damping: 30 }}
                  />
                )}
              </NavLink>
            );
          })}
          <button
            onClick={handleNewRun}
            disabled={submitting}
            className="ml-3 inline-flex items-center gap-1.5 px-3 py-1.5 text-sm font-medium rounded-lg bg-teal-600 text-white hover:bg-teal-700 transition-colors disabled:opacity-50"
          >
            <Plus className="w-4 h-4" />
            New Run
          </button>
        </div>
      </div>
    </nav>
  );
}
