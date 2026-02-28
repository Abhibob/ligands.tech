export interface Protein {
  id: string;
  name: string;
  fullName: string;
  type: string;
}

export interface Ligand {
  id: string;
  name: string;
  type: string;
  molecularWeight: string;
}

export interface Pair {
  id: string;
  proteinId: string;
  ligandId: string;
  score: number;
  bindingEnergy: number;
  kd: string;
  keyResidues: string[];
  researcherId: string;
  explainIdx: number;
}

export interface Researcher {
  id: string;
  name: string;
  specialty: string;
}
