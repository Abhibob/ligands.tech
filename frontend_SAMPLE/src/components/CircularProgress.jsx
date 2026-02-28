import { motion } from 'framer-motion';

export default function CircularProgress({ value, size = 56, strokeWidth = 4, color = 'var(--color-accent-blue)' }) {
  const radius = (size - strokeWidth) / 2;
  const circumference = 2 * Math.PI * radius;
  const filled = circumference * (1 - value / 100);

  return (
    <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`} className="block">
      {/* Track */}
      <circle
        cx={size / 2}
        cy={size / 2}
        r={radius}
        fill="none"
        stroke="rgba(255,255,255,0.06)"
        strokeWidth={strokeWidth}
      />
      {/* Fill */}
      <motion.circle
        cx={size / 2}
        cy={size / 2}
        r={radius}
        fill="none"
        stroke={color}
        strokeWidth={strokeWidth}
        strokeLinecap="round"
        strokeDasharray={circumference}
        initial={{ strokeDashoffset: circumference }}
        animate={{ strokeDashoffset: filled }}
        transition={{ duration: 0.6, ease: 'easeOut' }}
        transform={`rotate(-90 ${size / 2} ${size / 2})`}
      />
      {/* Center text */}
      <text
        x={size / 2}
        y={size / 2}
        textAnchor="middle"
        dominantBaseline="central"
        fill={color}
        fontSize={size * 0.22}
        fontFamily="monospace"
        fontWeight="bold"
      >
        {Math.round(value)}
      </text>
    </svg>
  );
}
