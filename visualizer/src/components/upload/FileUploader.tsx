import { useCallback, useState } from 'react';
import { useStore } from '../../state/store.ts';
import { loadLocalFile } from '../../loaders/localFile.ts';
import { isStructureFormat } from '../../parsers/fileDetect.ts';
import { parseMultiModelSdf, isMultiModelSdf } from '../../parsers/sdfParser.ts';
import { parsePlipXml } from '../../parsers/plipXmlParser.ts';
import { parseConfidenceJson, parseAffinityJson } from '../../parsers/boltzParser.ts';
import { parsePaeJson } from '../../parsers/paeParser.ts';

interface FileUploaderProps {
  onStructureLoad?: (fileId: string, content: string | ArrayBuffer, format: string) => void;
}

export default function FileUploader({ onStructureLoad }: FileUploaderProps) {
  const addFile = useStore((s) => s.addFile);
  const setGninaPoses = useStore((s) => s.setGninaPoses);
  const setPlipInteractions = useStore((s) => s.setPlipInteractions);
  const setBoltzConfidence = useStore((s) => s.setBoltzConfidence);
  const setBoltzAffinity = useStore((s) => s.setBoltzAffinity);
  const setPaeMatrix = useStore((s) => s.setPaeMatrix);
  const setLoading = useStore((s) => s.setLoading);
  const setError = useStore((s) => s.setError);
  const [isDragging, setIsDragging] = useState(false);

  const processFile = useCallback(async (file: File) => {
    setLoading(true);
    setError(null);
    try {
      const entry = await loadLocalFile(file);
      addFile(entry);

      const content = entry.content as string;

      // Handle structure formats — send to viewer
      if (isStructureFormat(entry.format)) {
        // Check for gnina multi-model SDF
        if (entry.format === 'sdf' && isMultiModelSdf(content)) {
          const poses = parseMultiModelSdf(content);
          setGninaPoses(poses);
        }
        onStructureLoad?.(entry.id, entry.content, entry.format);
      }

      // Handle PLIP XML
      if (entry.format === 'plip-xml') {
        const interactions = parsePlipXml(content);
        setPlipInteractions(interactions);
      }

      // Handle JSON files
      if (entry.format === 'confidence-json') {
        const conf = parseConfidenceJson(content);
        if (conf) setBoltzConfidence(conf);
        const aff = parseAffinityJson(content);
        if (aff) setBoltzAffinity(aff);
      }

      if (entry.format === 'pae-json') {
        const matrix = parsePaeJson(content);
        if (matrix) setPaeMatrix(matrix);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load file');
    } finally {
      setLoading(false);
    }
  }, [addFile, setGninaPoses, setPlipInteractions, setBoltzConfidence, setBoltzAffinity, setPaeMatrix, setLoading, setError, onStructureLoad]);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    const files = Array.from(e.dataTransfer.files);
    files.forEach(processFile);
  }, [processFile]);

  const handleFileInput = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(e.target.files ?? []);
    files.forEach(processFile);
  }, [processFile]);

  return (
    <div
      onDragOver={(e) => { e.preventDefault(); setIsDragging(true); }}
      onDragLeave={() => setIsDragging(false)}
      onDrop={handleDrop}
      className={`border-2 border-dashed rounded-lg p-4 text-center transition-colors cursor-pointer ${
        isDragging
          ? 'border-blue-500 bg-blue-50'
          : 'border-gray-300 hover:border-gray-400'
      }`}
    >
      <input
        type="file"
        onChange={handleFileInput}
        multiple
        accept=".pdb,.cif,.mmcif,.bcif,.sdf,.mol,.mol2,.pdbqt,.xyz,.json,.xml"
        className="hidden"
        id="file-upload"
      />
      <label htmlFor="file-upload" className="cursor-pointer">
        <p className="text-sm text-gray-600">
          Drop files here or <span className="text-blue-600 underline">browse</span>
        </p>
        <p className="text-xs text-gray-400 mt-1">
          PDB, CIF, SDF, MOL2, JSON, XML
        </p>
      </label>
    </div>
  );
}
