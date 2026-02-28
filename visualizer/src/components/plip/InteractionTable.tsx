import { useStore } from '../../state/store.ts';
import { INTERACTION_COLORS } from '../../utils/colors.ts';

export default function InteractionTable() {
  const interactions = useStore((s) => s.plipInteractions);
  const visible = useStore((s) => s.visibleInteractionTypes);

  const filtered = interactions.filter((i) => visible[i.type]);

  if (filtered.length === 0) return null;

  return (
    <div>
      <h4 className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-1">
        Details ({filtered.length})
      </h4>
      <div className="max-h-40 overflow-y-auto">
        <table className="w-full text-xs">
          <thead>
            <tr className="text-gray-500 border-b">
              <th className="text-left py-1">Type</th>
              <th className="text-left py-1">Residue</th>
              <th className="text-right py-1">Dist.</th>
            </tr>
          </thead>
          <tbody>
            {filtered.map((interaction, idx) => (
              <tr key={idx} className="hover:bg-gray-50">
                <td className="py-0.5">
                  <span
                    className="inline-block w-2 h-2 rounded-full mr-1"
                    style={{ backgroundColor: INTERACTION_COLORS[interaction.type] }}
                  />
                  {interaction.type.replace(/_/g, ' ')}
                </td>
                <td className="py-0.5">
                  {interaction.chain}:{interaction.residueName}{interaction.residueNumber}
                </td>
                <td className="text-right py-0.5">
                  {interaction.distance.toFixed(1)} A
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
