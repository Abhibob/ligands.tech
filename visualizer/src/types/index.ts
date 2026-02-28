export interface FileEntry {
  id: string;
  name: string;
  format: MolFormat;
  content: string | ArrayBuffer;
  source: 'local' | 'rcsb' | 'alphafold' | 'pubchem' | 'esmfold';
}

export type MolFormat =
  | 'pdb'
  | 'mmcif'
  | 'bcif'
  | 'sdf'
  | 'mol2'
  | 'pdbqt'
  | 'xyz'
  | 'pae-json'
  | 'confidence-json'
  | 'plip-xml'
  | 'unknown';

export type Representation = 'cartoon' | 'ball-and-stick' | 'surface' | 'spacefill';

export type ColorScheme = 'chain-id' | 'element-symbol' | 'plddt' | 'spectrum';
