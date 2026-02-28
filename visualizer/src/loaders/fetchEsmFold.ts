import type { FileEntry } from '../types/index.ts';
import { generateFileId } from '../state/store.ts';

const MAX_RESIDUES = 400;
const VALID_AA = /^[ACDEFGHIKLMNPQRSTVWY]+$/i;

/**
 * Submit an amino acid sequence to ESMFold for instant structure prediction.
 * Returns a PDB-format FileEntry. Max 400 residues.
 */
export async function fetchFromEsmFold(sequence: string): Promise<FileEntry> {
  const seq = sequence.trim().toUpperCase().replace(/\s+/g, '');

  if (!VALID_AA.test(seq)) {
    throw new Error('Invalid sequence: must contain only standard amino acid letters');
  }

  if (seq.length > MAX_RESIDUES) {
    throw new Error(`Sequence too long (${seq.length} residues). ESMFold limit is ${MAX_RESIDUES}.`);
  }

  if (seq.length < 10) {
    throw new Error('Sequence too short: need at least 10 residues');
  }

  const resp = await fetch('https://api.esmatlas.com/foldSequence/v1/pdb/', {
    method: 'POST',
    headers: { 'Content-Type': 'text/plain' },
    body: seq,
  });

  if (!resp.ok) {
    throw new Error(`ESMFold prediction failed (${resp.status})`);
  }

  const content = await resp.text();

  return {
    id: generateFileId(),
    name: `ESMFold-${seq.slice(0, 8)}.pdb`,
    format: 'pdb',
    content,
    source: 'esmfold',
  };
}
