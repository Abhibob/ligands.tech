import { useStore } from '../../state/store.ts';
import { lazy, Suspense } from 'react';

// Lazy-load Plotly to keep initial bundle small
const LazyPlot = lazy(() =>
  import('react-plotly.js').then((mod) => ({ default: mod.default }))
);

export default function PaeHeatmap() {
  const paeMatrix = useStore((s) => s.paeMatrix);

  if (!paeMatrix) return null;

  return (
    <div className="w-full">
      <h3 className="text-sm font-semibold text-gray-700 mb-2">Predicted Aligned Error</h3>
      <Suspense fallback={<div className="text-xs text-gray-400">Loading heatmap...</div>}>
        <LazyPlot
          data={[
            {
              z: paeMatrix,
              type: 'heatmap' as const,
              colorscale: [
                [0, '#0a5f38'],
                [0.5, '#c8e6c9'],
                [1, '#ffffff'],
              ],
              reversescale: false,
              colorbar: {
                title: { text: 'PAE (\u00C5)', side: 'right' as const },
              },
            },
          ]}
          layout={{
            height: 300,
            margin: { l: 50, r: 20, t: 10, b: 50 },
            xaxis: { title: { text: 'Scored residue' } },
            yaxis: { title: { text: 'Aligned residue' }, autorange: 'reversed' as const },
            autosize: true,
          }}
          config={{
            responsive: true,
            displayModeBar: false,
          }}
          style={{ width: '100%' }}
        />
      </Suspense>
    </div>
  );
}
