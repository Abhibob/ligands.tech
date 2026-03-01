import { BrowserRouter, Routes, Route, useLocation } from "react-router-dom";
import { AnimatePresence, motion } from "framer-motion";
import PageLayout from "./components/layout/PageLayout";
import HomePage from "./pages/HomePage";
import AgentsPage from "./pages/AgentsPage";
import FinishedAgentsPage from "./pages/FinishedAgentsPage";
import HypothesisPage from "./pages/HypothesisPage";
import ResultsPage from "./pages/ResultsPage";

function AnimatedRoutes() {
  const location = useLocation();

  return (
    <AnimatePresence mode="wait">
      <motion.div
        key={location.pathname}
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        transition={{ duration: 0.2 }}
      >
        <Routes location={location}>
          <Route element={<PageLayout />}>
            <Route path="/" element={<HomePage />} />
            <Route path="/agents/:id?" element={<AgentsPage />} />
            <Route path="/finished/:id?" element={<FinishedAgentsPage />} />
            <Route path="/hypothesis/:hypothesisId" element={<HypothesisPage />} />
            <Route path="/results" element={<ResultsPage />} />
          </Route>
        </Routes>
      </motion.div>
    </AnimatePresence>
  );
}

export default function App() {
  return (
    <BrowserRouter>
      <AnimatedRoutes />
    </BrowserRouter>
  );
}
