import { Suspense } from "react";
import { Canvas } from "@react-three/fiber";
import { Float } from "@react-three/drei";
import BindingModel from "./BindingModel";

interface MiniBindingSceneProps {
  pairId: string;
  score: number;
}

export default function MiniBindingScene({ pairId, score }: MiniBindingSceneProps) {
  return (
    <Canvas
      camera={{ position: [0, 0, 5], fov: 40 }}
      style={{ pointerEvents: "none" }}
      gl={{ antialias: false, alpha: true }}
      dpr={[1, 1.5]}
    >
      <ambientLight intensity={0.7} />
      <directionalLight position={[3, 3, 3]} intensity={0.6} />
      <Suspense fallback={null}>
        <Float speed={1.5} rotationIntensity={0.15} floatIntensity={0.3}>
          <BindingModel pairId={pairId} score={score} detail={false} />
        </Float>
      </Suspense>
    </Canvas>
  );
}
