import { useRef, useMemo } from "react";
import { useFrame } from "@react-three/fiber";
import * as THREE from "three";
import { Atom, Bond } from "./primitives";

// Seeded pseudo-random number generator
function seededRandom(seed: number) {
  let s = seed;
  return () => {
    s = (s * 16807 + 0) % 2147483647;
    return (s - 1) / 2147483646;
  };
}

function hashString(str: string): number {
  let hash = 0;
  for (let i = 0; i < str.length; i++) {
    const char = str.charCodeAt(i);
    hash = (hash << 5) - hash + char;
    hash |= 0;
  }
  return Math.abs(hash);
}

interface BindingModelProps {
  pairId: string;
  score: number;
  detail?: boolean;
}

export default function BindingModel({ pairId, score, detail = false }: BindingModelProps) {
  const groupRef = useRef<THREE.Group>(null);

  useFrame((_, delta) => {
    if (groupRef.current) {
      groupRef.current.rotation.y += delta * 0.2;
    }
  });

  const { atoms, bonds } = useMemo(() => {
    const rand = seededRandom(hashString(pairId));
    const proteinCount = detail ? 12 : 6;
    const ligandCount = detail ? 8 : 4;
    const atomRadius = detail ? 0.18 : 0.14;

    // Separation inversely proportional to score
    const separation = 1.8 - (score / 100) * 1.0;

    const atomList: { pos: [number, number, number]; color: string; radius: number }[] = [];
    const bondList: { start: [number, number, number]; end: [number, number, number]; color: string }[] = [];

    // Protein cluster (left, slate)
    const proteinPositions: [number, number, number][] = [];
    for (let i = 0; i < proteinCount; i++) {
      const pos: [number, number, number] = [
        -separation + (rand() - 0.5) * 1.2,
        (rand() - 0.5) * 1.4,
        (rand() - 0.5) * 1.2,
      ];
      proteinPositions.push(pos);
      atomList.push({ pos, color: "#64748b", radius: atomRadius * (0.8 + rand() * 0.4) });
    }

    // Bonds within protein cluster
    for (let i = 1; i < proteinPositions.length; i++) {
      const dist = new THREE.Vector3(...proteinPositions[i]).distanceTo(
        new THREE.Vector3(...proteinPositions[i - 1])
      );
      if (dist < 1.5) {
        bondList.push({ start: proteinPositions[i - 1], end: proteinPositions[i], color: "#94a3b8" });
      }
    }

    // Ligand cluster (right, teal)
    const ligandPositions: [number, number, number][] = [];
    for (let i = 0; i < ligandCount; i++) {
      const pos: [number, number, number] = [
        separation + (rand() - 0.5) * 0.9,
        (rand() - 0.5) * 1.1,
        (rand() - 0.5) * 0.9,
      ];
      ligandPositions.push(pos);
      atomList.push({ pos, color: "#0d9488", radius: atomRadius * (0.7 + rand() * 0.5) });
    }

    // Bonds within ligand cluster
    for (let i = 1; i < ligandPositions.length; i++) {
      const dist = new THREE.Vector3(...ligandPositions[i]).distanceTo(
        new THREE.Vector3(...ligandPositions[i - 1])
      );
      if (dist < 1.3) {
        bondList.push({ start: ligandPositions[i - 1], end: ligandPositions[i], color: "#5eead4" });
      }
    }

    // Cross-bonds colored by score tier
    const crossBondColor = score >= 70 ? "#059669" : score >= 40 ? "#d97706" : "#dc2626";
    const crossBondCount = score >= 70 ? 3 : score >= 40 ? 2 : 1;

    for (let i = 0; i < Math.min(crossBondCount, proteinPositions.length, ligandPositions.length); i++) {
      const pIdx = Math.floor(rand() * proteinPositions.length);
      const lIdx = Math.floor(rand() * ligandPositions.length);
      bondList.push({
        start: proteinPositions[pIdx],
        end: ligandPositions[lIdx],
        color: crossBondColor,
      });
    }

    return { atoms: atomList, bonds: bondList };
  }, [pairId, score, detail]);

  return (
    <group ref={groupRef}>
      {bonds.map((b, i) => (
        <Bond key={`b-${i}`} start={b.start} end={b.end} color={b.color} />
      ))}
      {atoms.map((a, i) => (
        <Atom key={`a-${i}`} position={a.pos} color={a.color} radius={a.radius} />
      ))}
    </group>
  );
}
