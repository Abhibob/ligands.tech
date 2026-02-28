import type { FileEntry } from '../types/index.ts';
import { generateFileId } from '../state/store.ts';

export async function fetchFromRcsb(pdbId: string): Promise<FileEntry> {
  const id = pdbId.toUpperCase().trim();

  // Try BinaryCIF first (smallest/fastest), fallback to text CIF
  const bcifUrl = `https://models.rcsb.org/${id}.bcif`;
  const cifUrl = `https://files.rcsb.org/download/${id}.cif`;

  try {
    const resp = await fetch(bcifUrl);
    if (resp.ok) {
      const buffer = await resp.arrayBuffer();
      return {
        id: generateFileId(),
        name: `${id}.bcif`,
        format: 'bcif',
        content: buffer,
        source: 'rcsb',
      };
    }
  } catch { /* fallback to text CIF */ }

  const resp = await fetch(cifUrl);
  if (!resp.ok) throw new Error(`PDB ID "${id}" not found on RCSB`);
  const content = await resp.text();

  return {
    id: generateFileId(),
    name: `${id}.cif`,
    format: 'mmcif',
    content,
    source: 'rcsb',
  };
}
