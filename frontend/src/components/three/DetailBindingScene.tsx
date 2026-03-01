import { Suspense } from "react";
import { Canvas } from "@react-three/fiber";
import { Float, OrbitControls, Html } from "@react-three/drei";
import BindingModel from "./BindingModel";

interface DetailBindingSceneProps {
  pairId: string;
  score: number;
  proteinName: string;
  ligandName: string;
}

function Labels({ proteinName, ligandName, score }: { proteinName: string; ligandName: string; score: number }) {
  const separation = 1.8 - (score / 100) * 1.0;
  return (
    <>
      <Html position={[-separation, 1.2, 0]} center>
        <div className="px-2 py-1 rounded bg-slate-700/80 text-white text-xs font-medium whitespace-nowrap backdrop-blur-sm">
          {proteinName}
        </div>
      </Html>
      <Html position={[separation, 1.2, 0]} center>
        <div className="px-2 py-1 rounded bg-teal-600/80 text-white text-xs font-medium whitespace-nowrap backdrop-blur-sm">
          {ligandName}
        </div>
      </Html>
    </>
  );
}

export default function DetailBindingScene({ pairId, score, proteinName, ligandName }: DetailBindingSceneProps) {
  return (
    <div className="w-full h-[400px] rounded-xl bg-gradient-to-br from-slate-50 to-slate-100 overflow-hidden">
      <Canvas camera={{ position: [0, 0, 6], fov: 45 }}>
        <ambientLight intensity={0.6} />
        <directionalLight position={[5, 5, 5]} intensity={0.8} />
        <directionalLight position={[-3, -3, 2]} intensity={0.3} />
        <Suspense fallback={null}>
          <Float speed={1.2} rotationIntensity={0.1} floatIntensity={0.2}>
            <BindingModel pairId={pairId} score={score} detail={true} />
            <Labels proteinName={proteinName} ligandName={ligandName} score={score} />
          </Float>
        </Suspense>
        <OrbitControls
          enableZoom={true}
          enablePan={false}
          autoRotate
          autoRotateSpeed={0.8}
          minDistance={3}
          maxDistance={10}
        />
      </Canvas>
    </div>
  );
}
