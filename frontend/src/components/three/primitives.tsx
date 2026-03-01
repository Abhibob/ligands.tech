import { useRef, useMemo } from "react";
import * as THREE from "three";

export function Atom({
  position,
  color,
  radius = 0.18,
}: {
  position: [number, number, number];
  color: string;
  radius?: number;
}) {
  return (
    <mesh position={position}>
      <sphereGeometry args={[radius, 16, 16]} />
      <meshStandardMaterial color={color} roughness={0.3} metalness={0.1} />
    </mesh>
  );
}

export function Bond({
  start,
  end,
  color = "#94a3b8",
}: {
  start: [number, number, number];
  end: [number, number, number];
  color?: string;
}) {
  const ref = useRef<THREE.Mesh>(null);
  const { midpoint, length, quaternion } = useMemo(() => {
    const s = new THREE.Vector3(...start);
    const e = new THREE.Vector3(...end);
    const mid = s.clone().add(e).multiplyScalar(0.5);
    const dir = e.clone().sub(s);
    const len = dir.length();
    const q = new THREE.Quaternion();
    q.setFromUnitVectors(new THREE.Vector3(0, 1, 0), dir.normalize());
    return { midpoint: mid, length: len, quaternion: q };
  }, [start, end]);

  return (
    <mesh ref={ref} position={midpoint} quaternion={quaternion}>
      <cylinderGeometry args={[0.04, 0.04, length, 8]} />
      <meshStandardMaterial color={color} roughness={0.4} />
    </mesh>
  );
}
