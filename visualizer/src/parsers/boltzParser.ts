import type { BoltzConfidence, BoltzAffinity } from '../types/boltz.ts';

export function parseConfidenceJson(jsonText: string): BoltzConfidence | null {
  try {
    const data = JSON.parse(jsonText);
    return {
      pTM: data.pTM ?? data.ptm ?? 0,
      ipTM: data.ipTM ?? data.iptm ?? 0,
      pLDDT: {
        mean: data.pLDDT?.mean ?? data.plddt?.mean ?? data.mean_plddt ?? 0,
        perResidue: data.pLDDT?.per_residue ?? data.plddt?.per_residue ?? data.per_residue_plddt,
      },
    };
  } catch {
    return null;
  }
}

export function parseAffinityJson(jsonText: string): BoltzAffinity | null {
  try {
    const data = JSON.parse(jsonText);
    return {
      binderProbability: data.binderProbability ?? data.binder_probability ?? 0,
      affinityValue: data.affinityValue ?? data.affinity_value ?? data.affinity ?? 0,
    };
  } catch {
    return null;
  }
}
