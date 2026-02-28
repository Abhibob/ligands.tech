import { useStore } from '../../state/store.ts';
import { cnnScoreColor } from '../../utils/colors.ts';

export default function PoseTable() {
  const poses = useStore((s) => s.gninaPoses);
  const activeIndex = useStore((s) => s.activePoseIndex);
  const setActivePose = useStore((s) => s.setActivePose);

  if (poses.length === 0) return null;

  return (
    <div>
      <h3 className="text-sm font-semibold text-gray-700 mb-2">Docking Poses</h3>
      <div className="overflow-x-auto">
        <table className="w-full text-xs">
          <thead>
            <tr className="text-gray-500 border-b">
              <th className="text-left py-1 px-1">#</th>
              <th className="text-right py-1 px-1">Energy</th>
              <th className="text-right py-1 px-1">CNN</th>
              <th className="text-right py-1 px-1">Aff.</th>
            </tr>
          </thead>
          <tbody>
            {poses.map((pose) => (
              <tr
                key={pose.index}
                onClick={() => setActivePose(pose.index)}
                className={`cursor-pointer transition-colors ${
                  activeIndex === pose.index
                    ? 'bg-blue-100 font-semibold'
                    : 'hover:bg-gray-50'
                }`}
              >
                <td className="py-1 px-1">{pose.index + 1}</td>
                <td className="text-right py-1 px-1">
                  {pose.minimizedAffinity?.toFixed(1) ?? '-'}
                </td>
                <td className="text-right py-1 px-1">
                  {pose.cnnScore != null ? (
                    <span style={{ color: cnnScoreColor(pose.cnnScore) }}>
                      {pose.cnnScore.toFixed(2)}
                    </span>
                  ) : '-'}
                </td>
                <td className="text-right py-1 px-1">
                  {pose.cnnAffinity?.toFixed(1) ?? '-'}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
