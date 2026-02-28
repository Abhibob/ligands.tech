import { useRef, useMemo } from "react";
import { Canvas, useFrame } from "@react-three/fiber";
import { Float, OrbitControls } from "@react-three/drei";
import * as THREE from "three";
import { Atom, Bond } from "../three/primitives";

function ProteinModel() {
  const groupRef = useRef<THREE.Group>(null);

  useFrame((_, delta) => {
    if (groupRef.current) {
      groupRef.current.rotation.y += delta * 0.15;
    }
  });

  const { atoms, bonds } = useMemo(() => {
    const atomList: { pos: [number, number, number]; color: string; radius: number }[] = [];
    const bondList: { start: [number, number, number]; end: [number, number, number] }[] = [];

    // Alpha helix backbone
    const backboneCount = 24;
    for (let i = 0; i < backboneCount; i++) {
      const t = i / backboneCount;
      const angle = t * Math.PI * 4;
      const helixRadius = 1.2;
      const x = Math.cos(angle) * helixRadius;
      const y = (t - 0.5) * 5;
      const z = Math.sin(angle) * helixRadius;
      const pos: [number, number, number] = [x, y, z];
      atomList.push({ pos, color: "#64748b", radius: 0.2 });

      if (i > 0) {
        bondList.push({ start: atomList[atomList.length - 2].pos, end: pos });
      }

      // Side chains every 3 residues
      if (i % 3 === 0) {
        const sideDir = new THREE.Vector3(x, 0, z).normalize();
        const sideLen = 0.6 + Math.random() * 0.4;
        const sidePos: [number, number, number] = [
          x + sideDir.x * sideLen,
          y + (Math.random() - 0.5) * 0.3,
          z + sideDir.z * sideLen,
        ];
        atomList.push({ pos: sidePos, color: "#0d9488", radius: 0.15 });
        bondList.push({ start: pos, end: sidePos });

        // Occasional branching
        if (i % 6 === 0) {
          const branchPos: [number, number, number] = [
            sidePos[0] + (Math.random() - 0.5) * 0.5,
            sidePos[1] + 0.4,
            sidePos[2] + (Math.random() - 0.5) * 0.5,
          ];
          atomList.push({ pos: branchPos, color: "#0d9488", radius: 0.12 });
          bondList.push({ start: sidePos, end: branchPos });
        }
      }
    }

    return { atoms: atomList, bonds: bondList };
  }, []);

  return (
    <Float speed={1.5} rotationIntensity={0.2} floatIntensity={0.5}>
      <group ref={groupRef}>
        {bonds.map((b, i) => (
          <Bond key={`b-${i}`} start={b.start} end={b.end} />
        ))}
        {atoms.map((a, i) => (
          <Atom key={`a-${i}`} position={a.pos} color={a.color} radius={a.radius} />
        ))}
      </group>
    </Float>
  );
}

export default function ProteinScene() {
  return (
    <div className="w-full h-full min-h-[600px]">
      <Canvas camera={{ position: [0, 0, 8], fov: 50 }}>
        <ambientLight intensity={0.6} />
        <directionalLight position={[5, 5, 5]} intensity={0.8} />
        <directionalLight position={[-3, -3, 2]} intensity={0.3} />
        <ProteinModel />
        <OrbitControls
          autoRotate
          autoRotateSpeed={1}
          enableZoom={false}
          enablePan={false}
        />
      </Canvas>
    </div>
  );
}
