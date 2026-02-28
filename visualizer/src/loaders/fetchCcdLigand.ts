import type { FileEntry } from '../types/index.ts';
import { generateFileId } from '../state/store.ts';

/**
 * Fetch a ligand by its CCD 3-letter code from RCSB Ligand Expo.
 * Returns the ideal (geometry-optimized) SDF coordinates.
 */
export async function fetchCcdLigand(ccdCode: string): Promise<FileEntry> {
  const code = ccdCode.toUpperCase().trim();
  const url = `https://files.rcsb.org/ligands/download/${code}_ideal.sdf`;

  const resp = await fetch(url);
  if (!resp.ok) throw new Error(`CCD ligand "${code}" not found on RCSB`);
  const content = await resp.text();

  if (!content.trim() || content.includes('not found')) {
    throw new Error(`CCD ligand "${code}" not found on RCSB`);
  }

  return {
    id: generateFileId(),
    name: `${code}.sdf`,
    format: 'sdf',
    content,
    source: 'rcsb',
  };
}
