import { useStore } from '../../state/store.ts';
import type { Representation, ColorScheme } from '../../types/index.ts';

const REPRESENTATIONS: { value: Representation; label: string }[] = [
  { value: 'cartoon', label: 'Cartoon' },
  { value: 'ball-and-stick', label: 'Ball & Stick' },
  { value: 'surface', label: 'Surface' },
  { value: 'spacefill', label: 'Spacefill' },
];

const COLOR_SCHEMES: { value: ColorScheme; label: string }[] = [
  { value: 'chain-id', label: 'By Chain' },
  { value: 'element-symbol', label: 'By Element' },
  { value: 'plddt', label: 'pLDDT' },
];

export default function ViewerControls() {
  const representation = useStore((s) => s.representation);
  const setRepresentation = useStore((s) => s.setRepresentation);
  const colorScheme = useStore((s) => s.colorScheme);
  const setColorScheme = useStore((s) => s.setColorScheme);

  return (
    <div className="space-y-3">
      <div>
        <h4 className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-1">Style</h4>
        <div className="flex flex-wrap gap-1">
          {REPRESENTATIONS.map((r) => (
            <button
              key={r.value}
              onClick={() => setRepresentation(r.value)}
              className={`px-2 py-1 text-xs rounded border transition-colors ${
                representation === r.value
                  ? 'bg-blue-600 text-white border-blue-600'
                  : 'bg-white text-gray-700 border-gray-300 hover:border-blue-400'
              }`}
            >
              {r.label}
            </button>
          ))}
        </div>
      </div>

      <div>
        <h4 className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-1">Color</h4>
        <div className="flex flex-wrap gap-1">
          {COLOR_SCHEMES.map((c) => (
            <button
              key={c.value}
              onClick={() => setColorScheme(c.value)}
              className={`px-2 py-1 text-xs rounded border transition-colors ${
                colorScheme === c.value
                  ? 'bg-blue-600 text-white border-blue-600'
                  : 'bg-white text-gray-700 border-gray-300 hover:border-blue-400'
              }`}
            >
              {c.label}
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}
