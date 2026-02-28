import { useParams, useNavigate } from "react-router-dom";
import { motion } from "framer-motion";
import { researchers, getPairsByResearcher, getResearcher } from "../data";
import ResearcherSidebar from "../components/researchers/ResearcherSidebar";
import PairCardGrid from "../components/researchers/PairCardGrid";

export default function ResearchersPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();

  const activeId = id || researchers[0].id;
  const researcher = getResearcher(activeId);
  const pairs = getPairsByResearcher(activeId);

  const handleChange = (researcherId: string) => {
    navigate(`/researchers/${researcherId}`);
  };

  return (
    <div className="max-w-7xl mx-auto px-6 py-10">
      <h1 className="text-3xl font-bold text-slate-900 mb-6">Researchers</h1>
      <div className="flex gap-6 min-h-[calc(100vh-12rem)]">
        <ResearcherSidebar activeId={activeId} onChange={handleChange} />

        <div className="flex-1 min-w-0">
          {researcher && (
            <motion.div
              key={activeId}
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.3 }}
              className="mb-6"
            >
              <p className="text-slate-500">
                <span className="font-medium text-slate-700" style={{ fontFamily: "Inter, sans-serif" }}>
                  {researcher.name}
                </span>{" "}
                &middot; {researcher.specialty} &middot;{" "}
                <span className="text-teal-600 font-medium">{pairs.length} pairs</span>
              </p>
            </motion.div>
          )}

          <PairCardGrid key={activeId} pairs={pairs} />
        </div>
      </div>
    </div>
  );
}
