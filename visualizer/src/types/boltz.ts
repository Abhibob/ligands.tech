export interface BoltzConfidence {
  pTM: number;
  ipTM: number;
  pLDDT: {
    mean: number;
    perResidue?: number[];
  };
}

export interface BoltzAffinity {
  binderProbability: number;
  affinityValue: number;
}
