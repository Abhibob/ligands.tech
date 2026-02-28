import type { FileEntry } from '../types/index.ts';
import { generateFileId } from '../state/store.ts';

export async function fetchFromAlphaFold(uniprotId: string): Promise<FileEntry> {
  const id = uniprotId.trim();

  // Use the AlphaFold API to get the current CIF URL (avoids hardcoding version)
  const apiUrl = `https://alphafold.ebi.ac.uk/api/prediction/${id}`;
  const apiResp = await fetch(apiUrl);
  if (!apiResp.ok) throw new Error(`No AlphaFold prediction found for UniProt ID "${id}"`);

  const entries = await apiResp.json();
  if (!Array.isArray(entries) || entries.length === 0) {
    throw new Error(`No AlphaFold prediction found for UniProt ID "${id}"`);
  }

  const cifUrl = entries[0].cifUrl;
  if (!cifUrl) throw new Error(`No CIF file available for UniProt ID "${id}"`);

  const resp = await fetch(cifUrl);
  if (!resp.ok) throw new Error(`Failed to download AlphaFold structure for UniProt ID "${id}"`);
  const content = await resp.text();

  return {
    id: generateFileId(),
    name: `AF-${id}.cif`,
    format: 'mmcif',
    content,
    source: 'alphafold',
  };
}
