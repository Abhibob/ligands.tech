import { useStore } from '../../state/store.ts';
import { INTERACTION_COLORS } from '../../utils/colors.ts';
import type { InteractionType } from '../../types/plip.ts';

const LABELS: Record<InteractionType, string> = {
  hydrogen_bond: 'H-bonds',
  hydrophobic: 'Hydrophobic',
  pi_stacking: 'Pi-stacking',
  salt_bridge: 'Salt bridges',
  water_bridge: 'Water bridges',
  halogen_bond: 'Halogen bonds',
  metal_complex: 'Metal complexes',
};

export default function InteractionOverlay() {
  const interactions = useStore((s) => s.plipInteractions);
  const visible = useStore((s) => s.visibleInteractionTypes);
  const toggle = useStore((s) => s.toggleInteractionType);

  if (interactions.length === 0) return null;

  // Count interactions by type
  const counts: Partial<Record<InteractionType, number>> = {};
  for (const i of interactions) {
    counts[i.type] = (counts[i.type] ?? 0) + 1;
  }

  return (
    <div>
      <h3 className="text-sm font-semibold text-gray-700 mb-2">Interactions</h3>
      <div className="space-y-1">
        {(Object.entries(counts) as [InteractionType, number][]).map(([type, count]) => (
          <label key={type} className="flex items-center gap-2 text-xs cursor-pointer">
            <input
              type="checkbox"
              checked={visible[type] ?? true}
              onChange={() => toggle(type)}
              className="rounded"
            />
            <span
              className="w-3 h-3 rounded-full inline-block"
              style={{ backgroundColor: INTERACTION_COLORS[type] }}
            />
            <span className="text-gray-700">{LABELS[type]}</span>
            <span className="text-gray-400 ml-auto">{count}</span>
          </label>
        ))}
      </div>
    </div>
  );
}
