import { useMemo } from 'react';

// Simple deterministic hash from string
function hash(str) {
  let h = 0;
  for (let i = 0; i < str.length; i++) {
    h = ((h << 5) - h + str.charCodeAt(i)) | 0;
  }
  return Math.abs(h);
}

// Seeded pseudo-random (deterministic per seed)
function seededRandom(seed) {
  let s = seed;
  return () => {
    s = (s * 16807 + 0) % 2147483647;
    return (s - 1) / 2147483646;
  };
}

export default function MiniMolecularViz({ proteinId, ligandId, score, width = 160, height = 100 }) {
  const { proteinNodes, ligandNodes, proteinEdges, ligandEdges, bindingLines } = useMemo(() => {
    const seed = hash(proteinId + ligandId);
    const rand = seededRandom(seed);

    // Protein cluster — left side
    const pCount = 4 + Math.floor(rand() * 2); // 4-5 nodes
    const pNodes = [];
    for (let i = 0; i < pCount; i++) {
      pNodes.push({
        x: 20 + rand() * 35,
        y: 18 + rand() * 64,
        r: 3 + rand() * 3,
      });
    }

    // Ligand cluster — right side
    const lCount = 3 + Math.floor(rand() * 2); // 3-4 nodes
    const lNodes = [];
    for (let i = 0; i < lCount; i++) {
      lNodes.push({
        x: 105 + rand() * 35,
        y: 18 + rand() * 64,
        r: 2.5 + rand() * 2.5,
      });
    }

    // Intra-cluster edges (connect nearby nodes)
    const pEdges = [];
    for (let i = 0; i < pNodes.length; i++) {
      for (let j = i + 1; j < pNodes.length; j++) {
        if (rand() < 0.5) pEdges.push([i, j]);
      }
    }

    const lEdges = [];
    for (let i = 0; i < lNodes.length; i++) {
      for (let j = i + 1; j < lNodes.length; j++) {
        if (rand() < 0.5) lEdges.push([i, j]);
      }
    }

    // Binding lines — count based on score
    const bCount = Math.max(1, Math.floor(score / 30));
    const bLines = [];
    for (let i = 0; i < bCount; i++) {
      const pIdx = Math.floor(rand() * pNodes.length);
      const lIdx = Math.floor(rand() * lNodes.length);
      bLines.push({
        x1: pNodes[pIdx].x + pNodes[pIdx].r,
        y1: pNodes[pIdx].y,
        x2: lNodes[lIdx].x - lNodes[lIdx].r,
        y2: lNodes[lIdx].y,
      });
    }

    return {
      proteinNodes: pNodes,
      ligandNodes: lNodes,
      proteinEdges: pEdges,
      ligandEdges: lEdges,
      bindingLines: bLines,
    };
  }, [proteinId, ligandId, score]);

  return (
    <svg
      width={width}
      height={height}
      viewBox={`0 0 ${width} ${height}`}
      className="block"
    >
      {/* Protein intra-cluster edges */}
      {proteinEdges.map(([i, j], idx) => (
        <line
          key={`pe-${idx}`}
          x1={proteinNodes[i].x}
          y1={proteinNodes[i].y}
          x2={proteinNodes[j].x}
          y2={proteinNodes[j].y}
          stroke="rgba(139, 92, 246, 0.25)"
          strokeWidth={0.8}
        />
      ))}

      {/* Ligand intra-cluster edges */}
      {ligandEdges.map(([i, j], idx) => (
        <line
          key={`le-${idx}`}
          x1={ligandNodes[i].x}
          y1={ligandNodes[i].y}
          x2={ligandNodes[j].x}
          y2={ligandNodes[j].y}
          stroke="rgba(59, 130, 246, 0.25)"
          strokeWidth={0.8}
        />
      ))}

      {/* Binding lines — dashed, animated */}
      {bindingLines.map((line, idx) => (
        <line
          key={`bl-${idx}`}
          x1={line.x1}
          y1={line.y1}
          x2={line.x2}
          y2={line.y2}
          stroke="rgba(6, 214, 160, 0.5)"
          strokeWidth={1}
          strokeDasharray="4 4"
          className="mini-viz-binding"
          style={{ animationDelay: `${idx * 0.3}s` }}
        />
      ))}

      {/* Protein nodes */}
      {proteinNodes.map((node, idx) => (
        <circle
          key={`pn-${idx}`}
          cx={node.x}
          cy={node.y}
          r={node.r}
          fill="rgba(139, 92, 246, 0.6)"
          className="mini-viz-node-glow"
          style={{ animationDelay: `${idx * 0.4}s` }}
        />
      ))}

      {/* Ligand nodes */}
      {ligandNodes.map((node, idx) => (
        <circle
          key={`ln-${idx}`}
          cx={node.x}
          cy={node.y}
          r={node.r}
          fill="rgba(59, 130, 246, 0.6)"
          className="mini-viz-node-glow"
          style={{ animationDelay: `${idx * 0.5 + 0.2}s` }}
        />
      ))}
    </svg>
  );
}
