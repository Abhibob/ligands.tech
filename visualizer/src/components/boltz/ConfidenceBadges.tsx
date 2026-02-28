import { useStore } from '../../state/store.ts';
import { plddtColor } from '../../utils/colors.ts';

export default function ConfidenceBadges() {
  const confidence = useStore((s) => s.boltzConfidence);

  if (!confidence) return null;

  return (
    <div>
      <h3 className="text-sm font-semibold text-gray-700 mb-2">Confidence</h3>
      <div className="flex flex-wrap gap-2">
        <Badge label="pTM" value={confidence.pTM} />
        <Badge label="ipTM" value={confidence.ipTM} />
        <Badge
          label="pLDDT"
          value={confidence.pLDDT.mean}
          color={plddtColor(confidence.pLDDT.mean)}
          isPercent
        />
      </div>
    </div>
  );
}

function Badge({
  label,
  value,
  color,
  isPercent,
}: {
  label: string;
  value: number;
  color?: string;
  isPercent?: boolean;
}) {
  const displayValue = isPercent ? value.toFixed(1) : value.toFixed(2);
  const bgColor = color ?? (value > 0.7 ? '#4CAF50' : value > 0.5 ? '#FFC107' : '#F44336');

  return (
    <div className="flex items-center gap-1 rounded-full border border-gray-200 px-2 py-0.5">
      <span className="text-xs text-gray-500">{label}</span>
      <span
        className="text-xs font-bold px-1.5 py-0.5 rounded-full text-white"
        style={{ backgroundColor: bgColor }}
      >
        {displayValue}
      </span>
    </div>
  );
}
