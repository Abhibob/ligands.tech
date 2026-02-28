export interface PdbStructure {
  pdbId: string;
  chainId: string;
  method: string;
  resolution: number | null;
  coverage: number;
  unpStart: number;
  unpEnd: number;
}

export interface ProteinResolution {
  accession: string;
  name: string;
  gene: string;
  synonyms: string[];
  organism: string;
  sequenceLength: number;
  bestStructures: PdbStructure[];
  alphafoldAvailable: boolean;
}

export interface LigandProperties {
  name: string;
  cid: number;
  formula: string;
  molecularWeight: number;
  smiles: string;
  xLogP: number | null;
  tpsa: number | null;
  hBondDonors: number | null;
  hBondAcceptors: number | null;
}

export interface LlmParsedQuery {
  intent: 'bind' | 'view_protein' | 'view_ligand' | 'unknown';
  proteinName: string | null;
  ligandName: string | null;
  raw: string;
}
