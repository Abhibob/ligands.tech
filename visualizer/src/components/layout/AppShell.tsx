import { useRef, useCallback } from 'react';
import MolstarViewer from '../viewer/MolstarViewer.tsx';
import type { MolstarViewerHandle } from '../viewer/MolstarViewer.tsx';
import Sidebar from './Sidebar.tsx';
import InfoPanel from './InfoPanel.tsx';
import PaeHeatmap from '../boltz/PaeHeatmap.tsx';
import { useStore } from '../../state/store.ts';
import {
  loadStructureData,
  loadBcifData,
} from '../../utils/molstarHelpers.ts';
import type { MolFormat } from '../../types/index.ts';

export default function AppShell() {
  const viewerRef = useRef<MolstarViewerHandle>(null);
  const paeMatrix = useStore((s) => s.paeMatrix);

  const handleStructureLoad = useCallback(
    async (fileId: string, content: string | ArrayBuffer, format: string) => {
      const plugin = viewerRef.current?.getPlugin();
      if (!plugin) return;

      const molFormat = format as MolFormat;

      if (molFormat === 'bcif' && content instanceof ArrayBuffer) {
        await loadBcifData(plugin, content, fileId);
      } else {
        await loadStructureData(plugin, content, molFormat, fileId);
      }
    },
    [],
  );

  return (
    <div className="w-full h-full flex flex-col">
      {/* Main area: sidebar + viewer + info panel */}
      <div className="flex-1 flex min-h-0">
        {/* Left Sidebar */}
        <div className="w-64 flex-shrink-0">
          <Sidebar onStructureLoad={handleStructureLoad} />
        </div>

        {/* Center: 3D Viewer */}
        <div className="flex-1 bg-gray-100 min-w-0">
          <MolstarViewer ref={viewerRef} />
        </div>

        {/* Right: Info Panel */}
        <div className="w-72 flex-shrink-0">
          <InfoPanel />
        </div>
      </div>

      {/* Bottom Panel: PAE Heatmap (only shown when data is loaded) */}
      {paeMatrix && (
        <div className="h-80 border-t border-gray-200 bg-white p-3 overflow-auto">
          <PaeHeatmap />
        </div>
      )}
    </div>
  );
}
