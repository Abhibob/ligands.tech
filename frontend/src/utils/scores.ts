import type { PipelineStep } from "../types";

/**
 * Derive a composite score (0-100) from pipeline steps.
 * Weighted: boltz binder_probability (40%), gnina cnn_score (40%), posebusters pass_rate (20%).
 * Only counts steps that have data; adjusts weights accordingly.
 */
export function deriveScore(steps: PipelineStep[]): number {
  let totalWeight = 0;
  let weighted = 0;

  for (const step of steps) {
    if (!step.confidence) continue;

    if (step.stepName === "boltz_predict" && step.confidence.binder_probability != null) {
      const prob = Number(step.confidence.binder_probability);
      weighted += prob * 100 * 0.4;
      totalWeight += 0.4;
    }
    if (step.stepName === "gnina_dock" && step.confidence.cnn_score != null) {
      // CNN score is 0-1, scale to 0-100
      const score = Number(step.confidence.cnn_score);
      weighted += score * 100 * 0.4;
      totalWeight += 0.4;
    }
    if (step.stepName === "posebusters_check" && step.confidence.pass_rate != null) {
      const rate = Number(step.confidence.pass_rate);
      weighted += rate * 100 * 0.2;
      totalWeight += 0.2;
    }
  }

  if (totalWeight === 0) return 0;
  return Math.round(weighted / totalWeight);
}

/**
 * Extract binding energy (kcal/mol) from the gnina docking step.
 */
export function deriveBindingEnergy(steps: PipelineStep[]): number | null {
  for (const step of steps) {
    if (step.stepName === "gnina_dock" && step.confidence?.energy_kcal_mol != null) {
      return Number(step.confidence.energy_kcal_mol);
    }
  }
  return null;
}

/**
 * Extract key residues from the PLIP profiling step.
 */
export function deriveKeyResidues(steps: PipelineStep[]): string[] {
  for (const step of steps) {
    if (step.stepName === "plip_profile" && step.confidence?.key_residues) {
      const residues = step.confidence.key_residues;
      if (Array.isArray(residues)) return residues.map(String);
    }
  }
  return [];
}
