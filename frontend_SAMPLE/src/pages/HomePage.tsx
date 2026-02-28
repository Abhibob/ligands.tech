import { Suspense } from "react";
import HeroSection from "../components/home/HeroSection";
import ProteinScene from "../components/home/ProteinScene";

export default function HomePage() {
  return (
    <div className="max-w-7xl mx-auto px-6">
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 min-h-[calc(100vh-4rem)]">
        <HeroSection />
        <div className="flex items-center justify-center min-h-[600px]">
          <Suspense
            fallback={
              <div className="w-full h-[600px] flex items-center justify-center text-slate-400">
                Loading 3D scene...
              </div>
            }
          >
            <ProteinScene />
          </Suspense>
        </div>
      </div>
    </div>
  );
}
