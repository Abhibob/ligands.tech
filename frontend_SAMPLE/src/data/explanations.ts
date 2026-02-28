import type { Protein, Ligand } from "../types";

type ExplainFn = (protein: Protein, ligand: Ligand, score: number) => string;

const templates: ExplainFn[] = [
  (protein, ligand, score) =>
    `${ligand.name} demonstrates ${score > 70 ? "strong" : score > 40 ? "moderate" : "weak"} binding affinity to the ${protein.name} active site. The compound forms ${score > 70 ? "three" : score > 40 ? "two" : "one"} hydrogen bond${score > 40 ? "s" : ""} with key residues in the ATP-binding pocket, with ${score > 70 ? "excellent" : score > 40 ? "adequate" : "poor"} shape complementarity to the catalytic domain.`,

  (protein, ligand, score) =>
    `Molecular docking reveals that ${ligand.name} ${score > 70 ? "tightly occupies" : score > 40 ? "partially fits into" : "loosely interacts with"} the binding groove of ${protein.name}. Hydrophobic interactions with Leu718, Val726, and Met793 ${score > 70 ? "stabilize the complex significantly" : score > 40 ? "provide moderate stabilization" : "are insufficient for stable binding"}.`,

  (protein, ligand, score) =>
    `The ${protein.name}-${ligand.name} interaction is characterized by ${score > 70 ? "extensive" : score > 40 ? "partial" : "minimal"} van der Waals contacts across the binding interface. ${score > 70 ? "A critical salt bridge with Asp855 anchors the ligand" : score > 40 ? "Weak electrostatic interactions are present" : "No significant electrostatic complementarity was observed"}.`,

  (protein, ligand, score) =>
    `Analysis of the ${protein.name} binding pocket shows ${score > 70 ? "optimal" : score > 40 ? "acceptable" : "suboptimal"} accommodation of ${ligand.name}. The ${ligand.type === "Monoclonal Antibody" ? "antibody epitope recognition" : "small molecule orientation"} results in a binding free energy of ${(-score * 0.12).toFixed(1)} kcal/mol, with ${score > 70 ? "favorable" : score > 40 ? "mixed" : "unfavorable"} entropic contributions.`,

  (protein, ligand, score) =>
    `${ligand.name} ${score > 70 ? "effectively inhibits" : score > 40 ? "partially modulates" : "fails to significantly affect"} ${protein.name} activity through ${score > 70 ? "competitive binding at the orthosteric site" : score > 40 ? "allosteric modulation" : "non-specific surface interactions"}. Key contact residues include Thr790, Met${Math.floor(700 + score)}, and Cys${Math.floor(750 + score)}.`,
];

export function getExplanation(
  protein: Protein,
  ligand: Ligand,
  score: number,
  explainIdx: number
): string {
  return templates[explainIdx](protein, ligand, score);
}

const detailedTemplates: ExplainFn[] = [
  (protein, ligand, score) =>
    `Further structural analysis of the ${protein.name}-${ligand.name} complex reveals ${score > 70 ? "a highly conserved binding mode across crystal structures" : score > 40 ? "some variability in the binding orientation" : "significant conformational heterogeneity"}. Water-mediated contacts at the binding interface ${score > 70 ? "contribute substantially to the overall affinity" : score > 40 ? "play a minor role in stabilization" : "are largely absent"}, suggesting that ${score > 70 ? "desolvation penalties are minimal" : score > 40 ? "partial desolvation occurs upon binding" : "unfavorable desolvation limits complex formation"}.`,

  (protein, ligand, score) =>
    `Molecular dynamics simulations indicate that the ${protein.name}-${ligand.name} complex ${score > 70 ? "maintains structural integrity over 100ns trajectories" : score > 40 ? "shows moderate fluctuations within the binding site" : "dissociates rapidly under physiological conditions"}. The root-mean-square deviation of the bound ligand is ${score > 70 ? "below 1.5 Å" : score > 40 ? "between 1.5-3.0 Å" : "above 3.0 Å"}, consistent with the observed binding affinity.`,

  (protein, ligand, score) =>
    `Comparative analysis with known ${protein.type} inhibitors places ${ligand.name} in the ${score > 70 ? "top quartile" : score > 40 ? "middle range" : "lower quartile"} of binding efficiency. The ligand efficiency index of ${(score * 0.005 + 0.1).toFixed(2)} kcal/mol per heavy atom ${score > 70 ? "exceeds the drug-likeness threshold" : score > 40 ? "meets minimum criteria for lead optimization" : "falls below acceptable limits for further development"}.`,

  (protein, ligand, score) =>
    `Thermodynamic profiling via isothermal titration calorimetry confirms ${score > 70 ? "an enthalpically-driven binding mechanism" : score > 40 ? "a mixed enthalpic-entropic binding profile" : "an entropically-unfavorable interaction"}. The ${ligand.type === "Monoclonal Antibody" ? "protein-protein" : "protein-small molecule"} interface buries ${score > 70 ? "approximately 850 Å² of solvent-accessible surface area" : score > 40 ? "roughly 550 Å² of contact surface" : "less than 350 Å² of surface area"}.`,

  (protein, ligand, score) =>
    `Selectivity profiling across a panel of related ${protein.type} targets indicates that ${ligand.name} demonstrates ${score > 70 ? "high selectivity for " + protein.name + " over off-target kinases" : score > 40 ? "moderate selectivity with some cross-reactivity" : "poor selectivity, with comparable binding to multiple targets"}. ${score > 70 ? "This specificity arises from unique contacts with gatekeeper residues" : score > 40 ? "Selectivity may be improved through scaffold modifications" : "Extensive SAR optimization would be required to achieve acceptable selectivity"}.`,
];

export function getDetailedExplanation(
  protein: Protein,
  ligand: Ligand,
  score: number,
  explainIdx: number
): string {
  return detailedTemplates[explainIdx](protein, ligand, score);
}
