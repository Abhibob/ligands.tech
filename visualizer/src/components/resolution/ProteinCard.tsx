import { useStore } from '../../state/store.ts';
import { downloadPdbStructure } from '../../loaders/fetchUniProt.ts';

export default function ProteinCard() {
  const resolution = useStore((s) => s.proteinResolution);
  const addFile = useStore((s) => s.addFile);
  const setLoading = useStore((s) => s.setLoading);
  const setError = useStore((s) => s.setError);

  if (!resolution) return null;

  const handleLoadStructure = async (pdbId: string) => {
    setLoading(true);
    setError(null);
    try {
      const entry = await downloadPdbStructure(pdbId);
      addFile(entry);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load structure');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div>
      <h3 className="text-sm font-semibold text-gray-700 mb-2">Protein</h3>
      <div className="space-y-1.5">
        <div className="text-sm font-medium text-gray-900">{resolution.name}</div>
        <div className="flex flex-wrap gap-x-3 gap-y-0.5 text-xs text-gray-500">
          <span>
            Gene: <span className="font-medium text-gray-700">{resolution.gene}</span>
          </span>
          <span>
            UniProt:{' '}
            <a
              href={`https://www.uniprot.org/uniprot/${resolution.accession}`}
              target="_blank"
              rel="noopener noreferrer"
              className="font-medium text-blue-600 hover:underline"
            >
              {resolution.accession}
            </a>
          </span>
          <span>{resolution.sequenceLength} aa</span>
        </div>

        {resolution.synonyms.length > 0 && (
          <div className="text-xs text-gray-400">
            Also: {resolution.synonyms.join(', ')}
          </div>
        )}

        {resolution.bestStructures.length > 0 && (
          <div className="mt-2">
            <div className="text-xs font-medium text-gray-600 mb-1">
              Top structures
            </div>
            <div className="max-h-32 overflow-y-auto">
              <table className="w-full text-xs">
                <thead>
                  <tr className="text-left text-gray-400">
                    <th className="pr-2">PDB</th>
                    <th className="pr-2">Res.</th>
                    <th className="pr-2">Method</th>
                    <th>Cov.</th>
                  </tr>
                </thead>
                <tbody>
                  {resolution.bestStructures.map((s) => (
                    <tr
                      key={`${s.pdbId}-${s.chainId}`}
                      className="hover:bg-blue-50 cursor-pointer"
                      onClick={() => handleLoadStructure(s.pdbId)}
                    >
                      <td className="pr-2 text-blue-600 font-medium">{s.pdbId}</td>
                      <td className="pr-2">
                        {s.resolution != null ? `${s.resolution.toFixed(1)}\u00C5` : '\u2014'}
                      </td>
                      <td className="pr-2 truncate max-w-[80px]" title={s.method}>
                        {s.method.replace(' diffraction', '').replace('Electron ', 'e')}
                      </td>
                      <td>{(s.coverage * 100).toFixed(0)}%</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {resolution.alphafoldAvailable && (
          <div className="text-xs text-gray-400 mt-1">
            AlphaFold prediction available
          </div>
        )}
      </div>
    </div>
  );
}
