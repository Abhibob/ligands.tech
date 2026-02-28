import type { MolFormat } from '../types/index.ts';

const EXTENSION_MAP: Record<string, MolFormat> = {
  '.pdb': 'pdb',
  '.ent': 'pdb',
  '.cif': 'mmcif',
  '.mmcif': 'mmcif',
  '.bcif': 'bcif',
  '.sdf': 'sdf',
  '.mol': 'sdf',
  '.mol2': 'mol2',
  '.pdbqt': 'pdbqt',
  '.xyz': 'xyz',
  '.pqr': 'pdb', // PQR is close enough to PDB for loading
};

export function detectFormat(filename: string, content?: string): MolFormat {
  const ext = filename.slice(filename.lastIndexOf('.')).toLowerCase();

  // JSON files need content inspection
  if (ext === '.json' && content) {
    try {
      const parsed = JSON.parse(content);
      if (Array.isArray(parsed) && parsed[0]?.predicted_aligned_error) return 'pae-json';
      if (parsed.predicted_aligned_error) return 'pae-json';
      if (parsed.pTM !== undefined || parsed.ptm !== undefined) return 'confidence-json';
      if (parsed.binderProbability !== undefined || parsed.binder_probability !== undefined) return 'confidence-json';
    } catch { /* not valid JSON */ }
    return 'unknown';
  }

  if (ext === '.xml') return 'plip-xml';

  return EXTENSION_MAP[ext] ?? 'unknown';
}

export function formatLabel(format: MolFormat): string {
  const labels: Record<MolFormat, string> = {
    'pdb': 'PDB',
    'mmcif': 'mmCIF',
    'bcif': 'BinaryCIF',
    'sdf': 'SDF',
    'mol2': 'MOL2',
    'pdbqt': 'PDBQT',
    'xyz': 'XYZ',
    'pae-json': 'PAE JSON',
    'confidence-json': 'Confidence JSON',
    'plip-xml': 'PLIP XML',
    'unknown': 'Unknown',
  };
  return labels[format];
}

export function isStructureFormat(format: MolFormat): boolean {
  return ['pdb', 'mmcif', 'bcif', 'sdf', 'mol2', 'pdbqt', 'xyz'].includes(format);
}

export function isProteinFormat(format: MolFormat): boolean {
  return ['pdb', 'mmcif', 'bcif', 'pdbqt'].includes(format);
}

export function isLigandFormat(format: MolFormat): boolean {
  return ['sdf', 'mol2'].includes(format);
}
