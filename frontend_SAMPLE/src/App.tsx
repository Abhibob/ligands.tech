import { BrowserRouter, Routes, Route, useLocation } from "react-router-dom";
import { AnimatePresence, motion } from "framer-motion";
import PageLayout from "./components/layout/PageLayout";
import HomePage from "./pages/HomePage";
import ResearchersPage from "./pages/ResearchersPage";
import InteractionPage from "./pages/InteractionPage";
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
            <Route path="/researchers/:id?" element={<ResearchersPage />} />
            <Route path="/interaction/:pairId" element={<InteractionPage />} />
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
