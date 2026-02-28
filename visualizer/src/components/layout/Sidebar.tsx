import { useStore } from '../../state/store.ts';
import { formatLabel } from '../../parsers/fileDetect.ts';
import FileUploader from '../upload/FileUploader.tsx';
import QueryInput from '../upload/QueryInput.tsx';
import ViewerControls from '../viewer/ViewerControls.tsx';
import PoseSelector from '../gnina/PoseSelector.tsx';

interface SidebarProps {
  onStructureLoad?: (fileId: string, content: string | ArrayBuffer, format: string) => void;
}

export default function Sidebar({ onStructureLoad }: SidebarProps) {
  const files = useStore((s) => s.files);
  const removeFile = useStore((s) => s.removeFile);
  const clearFiles = useStore((s) => s.clearFiles);
  const isLoading = useStore((s) => s.isLoading);
  const error = useStore((s) => s.error);

  return (
    <div className="h-full flex flex-col bg-white border-r border-gray-200 overflow-y-auto">
      <div className="p-3 border-b border-gray-200">
        <h1 className="text-sm font-bold text-gray-800">BindingOps Visualizer</h1>
      </div>

      <div className="p-3 space-y-4 flex-1">
        {/* File Upload */}
        <FileUploader onStructureLoad={onStructureLoad} />

        {/* Fetch by ID */}
        <QueryInput onStructureLoad={onStructureLoad} />

        {/* Loaded Files */}
        {files.length > 0 && (
          <div>
            <div className="flex items-center justify-between mb-1">
              <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wide">
                Files ({files.length})
              </h3>
              <button
                onClick={clearFiles}
                className="text-xs text-red-500 hover:text-red-700"
              >
                Clear All
              </button>
            </div>
            <div className="space-y-1">
              {files.map((f) => (
                <div
                  key={f.id}
                  className="flex items-center justify-between px-2 py-1 bg-gray-50 rounded text-xs group"
                >
                  <div className="flex items-center gap-1.5 truncate">
                    <span className="px-1 py-0.5 bg-blue-100 text-blue-700 rounded text-[10px] font-medium">
                      {formatLabel(f.format)}
                    </span>
                    <span className="text-gray-700 truncate">{f.name}</span>
                  </div>
                  <button
                    onClick={() => removeFile(f.id)}
                    className="text-gray-400 hover:text-red-500 opacity-0 group-hover:opacity-100 transition-opacity ml-1"
                  >
                    x
                  </button>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Viewer Controls */}
        <ViewerControls />

        {/* Pose Selector */}
        <PoseSelector />

        {/* Loading / Error */}
        {isLoading && (
          <div className="text-xs text-blue-600 animate-pulse">Loading...</div>
        )}
        {error && (
          <div className="text-xs text-red-600 bg-red-50 p-2 rounded">{error}</div>
        )}
      </div>
    </div>
  );
}
