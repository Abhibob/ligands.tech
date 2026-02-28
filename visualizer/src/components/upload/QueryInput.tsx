import { useState, useCallback } from 'react';
import { useStore } from '../../state/store.ts';
import { fetchFromRcsb } from '../../loaders/fetchRcsb.ts';
import { fetchFromAlphaFold } from '../../loaders/fetchAlphaFold.ts';
import { fetchFromPubChem } from '../../loaders/fetchPubChem.ts';
import { resolveProteinName } from '../../loaders/fetchUniProt.ts';
import { fetchCcdLigand } from '../../loaders/fetchCcdLigand.ts';
import { fetchLigandProperties } from '../../loaders/fetchLigandProperties.ts';
import { fetchFromEsmFold } from '../../loaders/fetchEsmFold.ts';
import { parseLlmQuery } from '../../loaders/parseLlmQuery.ts';

interface QueryInputProps {
  onStructureLoad?: (fileId: string, content: string | ArrayBuffer, format: string) => void;
}

type QueryType = 'protein' | 'pdb' | 'uniprot' | 'ligand' | 'sequence' | 'ask';

/** Heuristic: 2-3 uppercase letters → likely a CCD code (ATP, SAH, HEM) */
function looksLikeCcd(q: string): boolean {
  return /^[A-Z0-9]{2,3}$/.test(q.trim());
}

export default function QueryInput({ onStructureLoad }: QueryInputProps) {
  const [query, setQuery] = useState('');
  const [queryType, setQueryType] = useState<QueryType>('protein');
  const [apiKey, setApiKey] = useState('');
  const addFile = useStore((s) => s.addFile);
  const setLoading = useStore((s) => s.setLoading);
  const setError = useStore((s) => s.setError);
  const setProteinResolution = useStore((s) => s.setProteinResolution);
  const setLigandProperties = useStore((s) => s.setLigandProperties);

  const handleFetch = useCallback(async () => {
    if (!query.trim()) return;
    setLoading(true);
    setError(null);

    try {
      let entry;
      switch (queryType) {
        case 'protein': {
          const result = await resolveProteinName(query);
          setProteinResolution(result.resolution);
          entry = result.entry;
          break;
        }
        case 'pdb':
          entry = await fetchFromRcsb(query);
          break;
        case 'uniprot':
          entry = await fetchFromAlphaFold(query);
          break;
        case 'ligand': {
          const q = query.trim();
          // Try CCD first for short uppercase codes
          if (looksLikeCcd(q)) {
            try {
              entry = await fetchCcdLigand(q);
              // Also fetch properties for CCD ligands
              fetchLigandProperties(q)
                .then((props) => setLigandProperties(props))
                .catch(() => { /* properties are optional */ });
              break;
            } catch {
              // Not a valid CCD code, fall through to PubChem
            }
          }
          entry = await fetchFromPubChem(q);
          // Fetch properties in background
          fetchLigandProperties(q)
            .then((props) => setLigandProperties(props))
            .catch(() => { /* properties are optional */ });
          break;
        }
        case 'sequence':
          entry = await fetchFromEsmFold(query);
          break;
        case 'ask': {
          if (!apiKey.trim()) {
            throw new Error('API key required for natural language queries');
          }
          const parsed = await parseLlmQuery(query, apiKey);
          // Route based on parsed intent
          if (parsed.proteinName) {
            const result = await resolveProteinName(parsed.proteinName);
            setProteinResolution(result.resolution);
            entry = result.entry;
          }
          if (parsed.ligandName) {
            const ligandEntry = await fetchFromPubChem(parsed.ligandName);
            fetchLigandProperties(parsed.ligandName)
              .then((props) => setLigandProperties(props))
              .catch(() => {});
            if (!entry) {
              entry = ligandEntry;
            } else {
              // Load both protein and ligand
              addFile(ligandEntry);
              onStructureLoad?.(ligandEntry.id, ligandEntry.content, ligandEntry.format);
            }
          }
          if (!entry) {
            throw new Error(`Could not resolve query: "${query}"`);
          }
          break;
        }
      }
      addFile(entry);
      onStructureLoad?.(entry.id, entry.content, entry.format);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Fetch failed');
    } finally {
      setLoading(false);
    }
  }, [query, queryType, apiKey, addFile, setLoading, setError, setProteinResolution, setLigandProperties, onStructureLoad]);

  const placeholders: Record<QueryType, string> = {
    protein: 'EGFR, p53, CDK2...',
    pdb: '4HHB',
    uniprot: 'P00533',
    ligand: 'erlotinib, ATP...',
    sequence: 'MLEICLKLVGCKSKKGLSS...',
    ask: 'Does erlotinib bind EGFR?',
  };

  return (
    <div className="space-y-2">
      <div className="flex flex-wrap gap-1">
        {([
          { value: 'protein' as const, label: 'Protein' },
          { value: 'pdb' as const, label: 'PDB ID' },
          { value: 'uniprot' as const, label: 'UniProt' },
          { value: 'ligand' as const, label: 'Ligand' },
          { value: 'sequence' as const, label: 'Sequence' },
          { value: 'ask' as const, label: 'Ask' },
        ]).map(({ value, label }) => (
          <button
            key={value}
            onClick={() => setQueryType(value)}
            className={`px-2 py-0.5 text-xs rounded border transition-colors ${
              queryType === value
                ? 'bg-blue-600 text-white border-blue-600'
                : 'bg-white text-gray-700 border-gray-300 hover:border-blue-400'
            }`}
          >
            {label}
          </button>
        ))}
      </div>

      {queryType === 'ask' && (
        <input
          type="password"
          value={apiKey}
          onChange={(e) => setApiKey(e.target.value)}
          placeholder="LLM API key"
          className="w-full px-2 py-1 text-xs border border-gray-300 rounded focus:outline-none focus:border-blue-500"
        />
      )}

      <div className="flex gap-1">
        <input
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && handleFetch()}
          placeholder={placeholders[queryType]}
          className="flex-1 px-2 py-1 text-sm border border-gray-300 rounded focus:outline-none focus:border-blue-500"
        />
        <button
          onClick={handleFetch}
          className="px-3 py-1 text-sm bg-blue-600 text-white rounded hover:bg-blue-700 transition-colors"
        >
          Fetch
        </button>
      </div>

      {queryType === 'ask' && (
        <p className="text-xs text-amber-600">
          LLM may take 1-2 min on cold start.
        </p>
      )}

      {queryType === 'sequence' && (
        <p className="text-xs text-gray-400">
          Max 400 residues. Prediction takes a few seconds.
        </p>
      )}
    </div>
  );
}
