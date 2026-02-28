import { useStore } from '../../state/store.ts';

export default function PoseSelector() {
  const poses = useStore((s) => s.gninaPoses);
  const activeIndex = useStore((s) => s.activePoseIndex);
  const setActivePose = useStore((s) => s.setActivePose);

  if (poses.length <= 1) return null;

  return (
    <div className="flex items-center gap-2">
      <button
        onClick={() => setActivePose(Math.max(0, activeIndex - 1))}
        disabled={activeIndex === 0}
        className="px-2 py-0.5 text-xs rounded border border-gray-300 disabled:opacity-30 hover:bg-gray-100"
      >
        Prev
      </button>
      <input
        type="range"
        min={0}
        max={poses.length - 1}
        value={activeIndex}
        onChange={(e) => setActivePose(Number(e.target.value))}
        className="flex-1"
      />
      <button
        onClick={() => setActivePose(Math.min(poses.length - 1, activeIndex + 1))}
        disabled={activeIndex === poses.length - 1}
        className="px-2 py-0.5 text-xs rounded border border-gray-300 disabled:opacity-30 hover:bg-gray-100"
      >
        Next
      </button>
      <span className="text-xs text-gray-500 min-w-[3rem] text-right">
        {activeIndex + 1}/{poses.length}
      </span>
    </div>
  );
}
