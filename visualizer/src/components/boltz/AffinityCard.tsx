import { useStore } from '../../state/store.ts';

export default function AffinityCard() {
  const affinity = useStore((s) => s.boltzAffinity);

  if (!affinity) return null;

  const probColor = affinity.binderProbability > 0.7 ? 'text-green-600'
    : affinity.binderProbability > 0.4 ? 'text-yellow-600'
    : 'text-red-600';

  return (
    <div>
      <h3 className="text-sm font-semibold text-gray-700 mb-2">Affinity</h3>
      <div className="space-y-1 text-sm">
        <div className="flex justify-between">
          <span className="text-gray-500">Binder Prob.</span>
          <span className={`font-semibold ${probColor}`}>
            {(affinity.binderProbability * 100).toFixed(1)}%
          </span>
        </div>
        <div className="flex justify-between">
          <span className="text-gray-500">Affinity</span>
          <span className="font-semibold">{affinity.affinityValue.toFixed(2)}</span>
        </div>
      </div>
    </div>
  );
}
