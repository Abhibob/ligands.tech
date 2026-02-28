import type { Pair } from "../types";

export const pairs: Pair[] = [
  { id: "pair-01", proteinId: "protein-EGFR", ligandId: "ligand-erlotinib", score: 92, bindingEnergy: -11.04, kd: "0.3 nM", keyResidues: ["Thr790", "Met793", "Leu718"], researcherId: "researcher-1", explainIdx: 0 },
  { id: "pair-02", proteinId: "protein-BRAF", ligandId: "ligand-vemurafenib", score: 88, bindingEnergy: -10.56, kd: "1.2 nM", keyResidues: ["Cys532", "Trp531", "Phe583"], researcherId: "researcher-1", explainIdx: 1 },
  { id: "pair-03", proteinId: "protein-HER2", ligandId: "ligand-trastuzumab", score: 95, bindingEnergy: -11.4, kd: "0.1 nM", keyResidues: ["Domain IV", "Epitope 4D5"], researcherId: "researcher-1", explainIdx: 2 },
  { id: "pair-04", proteinId: "protein-KRAS", ligandId: "ligand-sotorasib", score: 85, bindingEnergy: -10.2, kd: "2.1 nM", keyResidues: ["Cys12", "His95", "Asp69"], researcherId: "researcher-2", explainIdx: 3 },
  { id: "pair-05", proteinId: "protein-VEGFR", ligandId: "ligand-bevacizumab", score: 79, bindingEnergy: -9.48, kd: "5.8 nM", keyResidues: ["VEGF-A interface", "Ig domain 2"], researcherId: "researcher-2", explainIdx: 4 },
  { id: "pair-06", proteinId: "protein-ALK", ligandId: "ligand-crizotinib", score: 90, bindingEnergy: -10.8, kd: "0.6 nM", keyResidues: ["Leu1196", "Gly1202", "Asp1203"], researcherId: "researcher-2", explainIdx: 0 },
  { id: "pair-07", proteinId: "protein-CDK4", ligandId: "ligand-palbociclib", score: 87, bindingEnergy: -10.44, kd: "1.5 nM", keyResidues: ["Val96", "Asp158", "His95"], researcherId: "researcher-3", explainIdx: 1 },
  { id: "pair-08", proteinId: "protein-TP53", ligandId: "ligand-imatinib", score: 34, bindingEnergy: -4.08, kd: "890 nM", keyResidues: ["Arg273", "Gly245"], researcherId: "researcher-3", explainIdx: 2 },
  { id: "pair-09", proteinId: "protein-EGFR", ligandId: "ligand-vemurafenib", score: 28, bindingEnergy: -3.36, kd: "1.4 μM", keyResidues: ["Leu718"], researcherId: "researcher-3", explainIdx: 3 },
  { id: "pair-10", proteinId: "protein-BRAF", ligandId: "ligand-erlotinib", score: 31, bindingEnergy: -3.72, kd: "1.1 μM", keyResidues: ["Trp531"], researcherId: "researcher-3", explainIdx: 4 },
  { id: "pair-11", proteinId: "protein-KRAS", ligandId: "ligand-imatinib", score: 22, bindingEnergy: -2.64, kd: "3.2 μM", keyResidues: ["Gly12"], researcherId: "researcher-4", explainIdx: 0 },
  { id: "pair-12", proteinId: "protein-HER2", ligandId: "ligand-erlotinib", score: 61, bindingEnergy: -7.32, kd: "45 nM", keyResidues: ["Thr862", "Leu726"], researcherId: "researcher-4", explainIdx: 1 },
  { id: "pair-13", proteinId: "protein-VEGFR", ligandId: "ligand-sotorasib", score: 18, bindingEnergy: -2.16, kd: "5.7 μM", keyResidues: ["Asp1046"], researcherId: "researcher-4", explainIdx: 2 },
  { id: "pair-14", proteinId: "protein-ALK", ligandId: "ligand-palbociclib", score: 41, bindingEnergy: -4.92, kd: "310 nM", keyResidues: ["Gly1202", "Leu1196"], researcherId: "researcher-5", explainIdx: 3 },
  { id: "pair-15", proteinId: "protein-CDK4", ligandId: "ligand-vemurafenib", score: 38, bindingEnergy: -4.56, kd: "520 nM", keyResidues: ["Val96"], researcherId: "researcher-5", explainIdx: 4 },
  { id: "pair-16", proteinId: "protein-TP53", ligandId: "ligand-crizotinib", score: 25, bindingEnergy: -3.0, kd: "2.5 μM", keyResidues: ["Arg248"], researcherId: "researcher-5", explainIdx: 0 },
  { id: "pair-17", proteinId: "protein-EGFR", ligandId: "ligand-sotorasib", score: 45, bindingEnergy: -5.4, kd: "180 nM", keyResidues: ["Met793", "Cys797"], researcherId: "researcher-5", explainIdx: 1 },
];
