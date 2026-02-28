import { Link, useLocation } from 'react-router-dom';
import { Upload, Users, FlaskConical, Trophy } from 'lucide-react';
import { motion } from 'framer-motion';

const navItems = [
  { path: '/', label: 'Upload', icon: Upload },
  { path: '/agents', label: 'Agents', icon: Users },
  { path: '/results', label: 'Results', icon: Trophy },
];

export default function Layout({ children }) {
  const location = useLocation();

  const activeKey = navItems.find(
    n => location.pathname === n.path || (n.path === '/agents' && location.pathname.startsWith('/agents'))
  )?.path;

  return (
    <div className="min-h-screen grid-bg">
      <nav className="fixed top-0 left-0 right-0 z-50 nav-gradient-line bg-bg-primary/80 backdrop-blur-xl">
        <div className="max-w-7xl mx-auto px-6 h-16 flex items-center justify-between">
          <Link to="/" className="flex items-center gap-2.5 no-underline">
            <div className="w-9 h-9 rounded-lg bg-cyan-glow/10 border border-cyan-glow/30 flex items-center justify-center">
              <FlaskConical size={18} className="text-cyan-glow" />
            </div>
            <span className="text-lg font-bold tracking-tight text-white">
              Protein<span className="text-cyan-glow">Bind</span>
            </span>
          </Link>

          <div className="flex items-center gap-1 relative">
            {navItems.map(({ path, label, icon: Icon }) => {
              const isActive = path === activeKey;
              return (
                <Link
                  key={path}
                  to={path}
                  className="relative flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium no-underline transition-colors text-slate-400 hover:text-slate-200"
                >
                  {isActive && (
                    <motion.div
                      layoutId="nav-pill"
                      className="absolute inset-0 rounded-lg bg-cyan-glow/10"
                      transition={{ type: 'spring', stiffness: 350, damping: 28 }}
                    />
                  )}
                  <Icon size={16} className={`relative z-10 ${isActive ? 'text-cyan-glow' : ''}`} />
                  <span className={`relative z-10 ${isActive ? 'text-cyan-glow' : ''}`}>{label}</span>
                </Link>
              );
            })}
          </div>

          <div className="flex items-center gap-2 text-xs text-slate-500 font-mono">
            <span className="w-1.5 h-1.5 rounded-full bg-cyan-glow" />
            <span>5 agents · 17 pairs</span>
          </div>
        </div>
      </nav>

      <main className="pt-16">
        <motion.div
          key={location.pathname}
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ duration: 0.25 }}
        >
          {children}
        </motion.div>
      </main>
    </div>
  );
}
