import { useEffect, useRef } from 'react';
import { motion } from 'framer-motion';

function randomBetween(a, b) {
  return a + Math.random() * (b - a);
}

function generateProteinNodes(cx, cy) {
  const nodes = [];
  for (let i = 0; i < 12; i++) {
    const angle = (i / 12) * Math.PI * 2 + randomBetween(-0.2, 0.2);
    const r = randomBetween(30, 65);
    nodes.push({ x: cx + Math.cos(angle) * r, y: cy + Math.sin(angle) * r });
  }
  for (let i = 0; i < 5; i++) {
    const angle = (i / 5) * Math.PI * 2;
    const r = randomBetween(10, 25);
    nodes.push({ x: cx + Math.cos(angle) * r, y: cy + Math.sin(angle) * r });
  }
  return nodes;
}

function generateLigandNodes(cx, cy) {
  const nodes = [];
  const count = 6;
  for (let i = 0; i < count; i++) {
    const angle = (i / count) * Math.PI * 2;
    const r = randomBetween(15, 30);
    nodes.push({ x: cx + Math.cos(angle) * r, y: cy + Math.sin(angle) * r });
  }
  nodes.push({ x: cx, y: cy });
  return nodes;
}

export default function MolecularViz({ score, proteinName, ligandName }) {
  const canvasRef = useRef(null);
  const animRef = useRef(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    const W = 600, H = 400;
    canvas.width = W * 2;
    canvas.height = H * 2;
    ctx.scale(2, 2);

    const proteinCenter = { x: 200, y: 200 };
    const ligandCenter = { x: 420, y: 200 };
    const proteinNodes = generateProteinNodes(proteinCenter.x, proteinCenter.y);
    const ligandNodes = generateLigandNodes(ligandCenter.x, ligandCenter.y);

    const bindingCount = Math.max(1, Math.floor(score / 20));
    const bindings = [];
    for (let i = 0; i < bindingCount; i++) {
      const pi = Math.floor(i * (proteinNodes.length / bindingCount)) % proteinNodes.length;
      const li = Math.floor(i * (ligandNodes.length / bindingCount)) % ligandNodes.length;
      bindings.push({ from: proteinNodes[pi], to: ligandNodes[li] });
    }

    const particles = [];
    for (let i = 0; i < 30; i++) {
      particles.push({
        x: randomBetween(0, W),
        y: randomBetween(0, H),
        vx: randomBetween(-0.3, 0.3),
        vy: randomBetween(-0.3, 0.3),
        r: randomBetween(1, 2.5),
        opacity: randomBetween(0.1, 0.4),
      });
    }

    let t = 0;
    const scoreAlpha = Math.min(score / 100, 1);

    function draw() {
      t += 0.02;
      ctx.clearRect(0, 0, W, H);

      // background particles
      for (const p of particles) {
        p.x += p.vx;
        p.y += p.vy;
        if (p.x < 0) p.x = W;
        if (p.x > W) p.x = 0;
        if (p.y < 0) p.y = H;
        if (p.y > H) p.y = 0;
        ctx.beginPath();
        ctx.arc(p.x, p.y, p.r, 0, Math.PI * 2);
        ctx.fillStyle = `rgba(6, 214, 160, ${p.opacity})`;
        ctx.fill();
      }

      // protein edges
      ctx.strokeStyle = 'rgba(139, 92, 246, 0.3)';
      ctx.lineWidth = 1;
      for (let i = 0; i < proteinNodes.length; i++) {
        for (let j = i + 1; j < proteinNodes.length; j++) {
          const dx = proteinNodes[i].x - proteinNodes[j].x;
          const dy = proteinNodes[i].y - proteinNodes[j].y;
          if (Math.sqrt(dx * dx + dy * dy) < 55) {
            ctx.beginPath();
            ctx.moveTo(proteinNodes[i].x, proteinNodes[i].y);
            ctx.lineTo(proteinNodes[j].x, proteinNodes[j].y);
            ctx.stroke();
          }
        }
      }

      // protein nodes
      for (const node of proteinNodes) {
        const pulse = Math.sin(t + node.x * 0.05) * 2;
        ctx.beginPath();
        ctx.arc(node.x, node.y, 4 + pulse, 0, Math.PI * 2);
        ctx.fillStyle = 'rgba(139, 92, 246, 0.8)';
        ctx.fill();
        ctx.beginPath();
        ctx.arc(node.x, node.y, 7 + pulse, 0, Math.PI * 2);
        ctx.fillStyle = 'rgba(139, 92, 246, 0.15)';
        ctx.fill();
      }

      // ligand edges
      ctx.strokeStyle = 'rgba(59, 130, 246, 0.4)';
      ctx.lineWidth = 1.5;
      for (let i = 0; i < ligandNodes.length; i++) {
        for (let j = i + 1; j < ligandNodes.length; j++) {
          const dx = ligandNodes[i].x - ligandNodes[j].x;
          const dy = ligandNodes[i].y - ligandNodes[j].y;
          if (Math.sqrt(dx * dx + dy * dy) < 45) {
            ctx.beginPath();
            ctx.moveTo(ligandNodes[i].x, ligandNodes[i].y);
            ctx.lineTo(ligandNodes[j].x, ligandNodes[j].y);
            ctx.stroke();
          }
        }
      }

      // ligand nodes
      for (const node of ligandNodes) {
        const pulse = Math.sin(t * 1.2 + node.y * 0.05) * 1.5;
        ctx.beginPath();
        ctx.arc(node.x, node.y, 3.5 + pulse, 0, Math.PI * 2);
        ctx.fillStyle = 'rgba(59, 130, 246, 0.9)';
        ctx.fill();
        ctx.beginPath();
        ctx.arc(node.x, node.y, 6 + pulse, 0, Math.PI * 2);
        ctx.fillStyle = 'rgba(59, 130, 246, 0.15)';
        ctx.fill();
      }

      // binding interactions
      for (const b of bindings) {
        const dashOffset = t * 30;
        ctx.save();
        ctx.setLineDash([4, 6]);
        ctx.lineDashOffset = -dashOffset;
        ctx.strokeStyle = `rgba(6, 214, 160, ${0.2 + scoreAlpha * 0.5})`;
        ctx.lineWidth = 1.5;
        ctx.beginPath();
        ctx.moveTo(b.from.x, b.from.y);
        const mx = (b.from.x + b.to.x) / 2;
        const my = (b.from.y + b.to.y) / 2 + Math.sin(t) * 10;
        ctx.quadraticCurveTo(mx, my, b.to.x, b.to.y);
        ctx.stroke();
        ctx.restore();

        const progress = ((t * 0.5) % 1);
        const px = b.from.x + (b.to.x - b.from.x) * progress;
        const py = b.from.y + (b.to.y - b.from.y) * progress + Math.sin(t) * 5 * (1 - Math.abs(progress - 0.5) * 2);
        ctx.beginPath();
        ctx.arc(px, py, 2.5, 0, Math.PI * 2);
        ctx.fillStyle = `rgba(6, 214, 160, ${0.5 + scoreAlpha * 0.5})`;
        ctx.fill();
      }

      // labels
      ctx.font = '11px monospace';
      ctx.textAlign = 'center';
      ctx.fillStyle = 'rgba(139, 92, 246, 0.8)';
      ctx.fillText(proteinName, proteinCenter.x, proteinCenter.y + 85);
      ctx.fillStyle = 'rgba(59, 130, 246, 0.8)';
      ctx.fillText(ligandName, ligandCenter.x, ligandCenter.y + 50);

      animRef.current = requestAnimationFrame(draw);
    }

    draw();
    return () => {
      if (animRef.current) cancelAnimationFrame(animRef.current);
    };
  }, [score, proteinName, ligandName]);

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ duration: 0.8 }}
      className="w-full rounded-xl border border-border-subtle bg-bg-card overflow-hidden relative"
    >
      {/* Overlay label top-left */}
      <div className="absolute top-3 left-4 text-[10px] font-mono text-slate-500 tracking-wide z-10">
        Protein-Ligand Interaction Model
      </div>

      {/* Scale indicator top-right */}
      <div className="absolute top-3 right-4 flex items-center gap-1.5 text-[10px] font-mono text-slate-600 z-10">
        <div className="w-8 h-px bg-slate-600" />
        10 nm
      </div>

      <canvas
        ref={canvasRef}
        style={{ width: 600, height: 400 }}
        className="w-full h-auto"
      />

      {/* Legend row below canvas */}
      <div className="flex items-center justify-center gap-6 px-4 py-2.5 border-t border-border-subtle/50 bg-bg-primary/30">
        <div className="flex items-center gap-1.5 text-[11px] text-slate-400">
          <span className="w-2.5 h-2.5 rounded-full bg-accent-purple" />
          Protein nodes
        </div>
        <div className="flex items-center gap-1.5 text-[11px] text-slate-400">
          <span className="w-2.5 h-2.5 rounded-full bg-accent-blue" />
          Ligand nodes
        </div>
        <div className="flex items-center gap-1.5 text-[11px] text-slate-400">
          <span className="w-2.5 h-2.5 rounded-full bg-cyan-glow" />
          Binding interactions
        </div>
      </div>
    </motion.div>
  );
}
