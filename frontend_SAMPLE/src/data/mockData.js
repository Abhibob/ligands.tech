const proteins = [
  { id: 'TP53', name: 'TP53', fullName: 'Tumor Protein P53', type: 'Tumor Suppressor' },
  { id: 'EGFR', name: 'EGFR', fullName: 'Epidermal Growth Factor Receptor', type: 'Receptor Tyrosine Kinase' },
  { id: 'BRAF', name: 'BRAF', fullName: 'B-Raf Proto-Oncogene', type: 'Serine/Threonine Kinase' },
  { id: 'HER2', name: 'HER2', fullName: 'Human Epidermal Growth Factor Receptor 2', type: 'Receptor Tyrosine Kinase' },
  { id: 'KRAS', name: 'KRAS', fullName: 'KRAS Proto-Oncogene', type: 'GTPase' },
  { id: 'VEGFR', name: 'VEGFR', fullName: 'Vascular Endothelial Growth Factor Receptor', type: 'Receptor Tyrosine Kinase' },
  { id: 'ALK', name: 'ALK', fullName: 'Anaplastic Lymphoma Kinase', type: 'Receptor Tyrosine Kinase' },
  { id: 'CDK4', name: 'CDK4', fullName: 'Cyclin Dependent Kinase 4', type: 'Serine/Threonine Kinase' },
];

const ligands = [
  { id: 'imatinib', name: 'Imatinib', type: 'Small Molecule', mw: '493.6 Da' },
  { id: 'erlotinib', name: 'Erlotinib', type: 'Small Molecule', mw: '393.4 Da' },
  { id: 'vemurafenib', name: 'Vemurafenib', type: 'Small Molecule', mw: '489.9 Da' },
  { id: 'trastuzumab', name: 'Trastuzumab', type: 'Monoclonal Antibody', mw: '148 kDa' },
  { id: 'sotorasib', name: 'Sotorasib', type: 'Small Molecule', mw: '560.6 Da' },
  { id: 'bevacizumab', name: 'Bevacizumab', type: 'Monoclonal Antibody', mw: '149 kDa' },
  { id: 'crizotinib', name: 'Crizotinib', type: 'Small Molecule', mw: '450.3 Da' },
  { id: 'palbociclib', name: 'Palbociclib', type: 'Small Molecule', mw: '447.5 Da' },
];

const explanations = [
  (p, l, score) => `${l.name} demonstrates ${score > 70 ? 'strong' : score > 40 ? 'moderate' : 'weak'} binding affinity to the ${p.name} active site. The compound forms ${score > 70 ? 'three' : score > 40 ? 'two' : 'one'} hydrogen bond${score > 40 ? 's' : ''} with key residues in the ATP-binding pocket, with ${score > 70 ? 'excellent' : score > 40 ? 'adequate' : 'poor'} shape complementarity to the catalytic domain.`,
  (p, l, score) => `Molecular docking reveals that ${l.name} ${score > 70 ? 'tightly occupies' : score > 40 ? 'partially fits into' : 'loosely interacts with'} the binding groove of ${p.name}. Hydrophobic interactions with Leu718, Val726, and Met793 ${score > 70 ? 'stabilize the complex significantly' : score > 40 ? 'provide moderate stabilization' : 'are insufficient for stable binding'}.`,
  (p, l, score) => `The ${p.name}-${l.name} interaction is characterized by ${score > 70 ? 'extensive' : score > 40 ? 'partial' : 'minimal'} van der Waals contacts across the binding interface. ${score > 70 ? 'A critical salt bridge with Asp855 anchors the ligand' : score > 40 ? 'Weak electrostatic interactions are present' : 'No significant electrostatic complementarity was observed'}.`,
  (p, l, score) => `Analysis of the ${p.name} binding pocket shows ${score > 70 ? 'optimal' : score > 40 ? 'acceptable' : 'suboptimal'} accommodation of ${l.name}. The ${l.type === 'Monoclonal Antibody' ? 'antibody epitope recognition' : 'small molecule orientation'} results in a binding free energy of ${(-score * 0.12).toFixed(1)} kcal/mol, with ${score > 70 ? 'favorable' : score > 40 ? 'mixed' : 'unfavorable'} entropic contributions.`,
  (p, l, score) => `${l.name} ${score > 70 ? 'effectively inhibits' : score > 40 ? 'partially modulates' : 'fails to significantly affect'} ${p.name} activity through ${score > 70 ? 'competitive binding at the orthosteric site' : score > 40 ? 'allosteric modulation' : 'non-specific surface interactions'}. Key contact residues include Thr790, Met${Math.floor(700 + score)}, and Cys${Math.floor(750 + score)}.`,
];

const pairs = [
  { id: 'pair-01', proteinId: 'EGFR', ligandId: 'erlotinib', score: 92, agentId: 'agent-1', bindingEnergy: -11.04, keyResidues: ['Thr790', 'Met793', 'Leu718'], affinityKd: '0.3 nM', explainIdx: 0 },
  { id: 'pair-02', proteinId: 'BRAF', ligandId: 'vemurafenib', score: 88, agentId: 'agent-1', bindingEnergy: -10.56, keyResidues: ['Cys532', 'Trp531', 'Phe583'], affinityKd: '1.2 nM', explainIdx: 1 },
  { id: 'pair-03', proteinId: 'HER2', ligandId: 'trastuzumab', score: 95, agentId: 'agent-1', bindingEnergy: -11.40, keyResidues: ['Domain IV', 'Epitope 4D5'], affinityKd: '0.1 nM', explainIdx: 2 },
  { id: 'pair-04', proteinId: 'KRAS', ligandId: 'sotorasib', score: 85, agentId: 'agent-2', bindingEnergy: -10.20, keyResidues: ['Cys12', 'His95', 'Asp69'], affinityKd: '2.1 nM', explainIdx: 3 },
  { id: 'pair-05', proteinId: 'VEGFR', ligandId: 'bevacizumab', score: 79, agentId: 'agent-2', bindingEnergy: -9.48, keyResidues: ['VEGF-A interface', 'Ig domain 2'], affinityKd: '5.8 nM', explainIdx: 4 },
  { id: 'pair-06', proteinId: 'ALK', ligandId: 'crizotinib', score: 90, agentId: 'agent-2', bindingEnergy: -10.80, keyResidues: ['Leu1196', 'Gly1202', 'Asp1203'], affinityKd: '0.6 nM', explainIdx: 0 },
  { id: 'pair-07', proteinId: 'CDK4', ligandId: 'palbociclib', score: 87, agentId: 'agent-3', bindingEnergy: -10.44, keyResidues: ['Val96', 'Asp158', 'His95'], affinityKd: '1.5 nM', explainIdx: 1 },
  { id: 'pair-08', proteinId: 'TP53', ligandId: 'imatinib', score: 34, agentId: 'agent-3', bindingEnergy: -4.08, keyResidues: ['Arg273', 'Gly245'], affinityKd: '890 nM', explainIdx: 2 },
  { id: 'pair-09', proteinId: 'EGFR', ligandId: 'vemurafenib', score: 28, agentId: 'agent-3', bindingEnergy: -3.36, keyResidues: ['Leu718'], affinityKd: '1.4 uM', explainIdx: 3 },
  { id: 'pair-10', proteinId: 'BRAF', ligandId: 'erlotinib', score: 31, agentId: 'agent-3', bindingEnergy: -3.72, keyResidues: ['Trp531'], affinityKd: '1.1 uM', explainIdx: 4 },
  { id: 'pair-11', proteinId: 'KRAS', ligandId: 'imatinib', score: 22, agentId: 'agent-4', bindingEnergy: -2.64, keyResidues: ['Gly12'], affinityKd: '3.2 uM', explainIdx: 0 },
  { id: 'pair-12', proteinId: 'HER2', ligandId: 'erlotinib', score: 61, agentId: 'agent-4', bindingEnergy: -7.32, keyResidues: ['Thr862', 'Leu726'], affinityKd: '45 nM', explainIdx: 1 },
  { id: 'pair-13', proteinId: 'VEGFR', ligandId: 'sotorasib', score: 18, agentId: 'agent-4', bindingEnergy: -2.16, keyResidues: ['Asp1046'], affinityKd: '5.7 uM', explainIdx: 2 },
  { id: 'pair-14', proteinId: 'ALK', ligandId: 'palbociclib', score: 41, agentId: 'agent-5', bindingEnergy: -4.92, keyResidues: ['Gly1202', 'Leu1196'], affinityKd: '310 nM', explainIdx: 3 },
  { id: 'pair-15', proteinId: 'CDK4', ligandId: 'vemurafenib', score: 38, agentId: 'agent-5', bindingEnergy: -4.56, keyResidues: ['Val96'], affinityKd: '520 nM', explainIdx: 4 },
  { id: 'pair-16', proteinId: 'TP53', ligandId: 'crizotinib', score: 25, agentId: 'agent-5', bindingEnergy: -3.00, keyResidues: ['Arg248'], affinityKd: '2.5 uM', explainIdx: 0 },
  { id: 'pair-17', proteinId: 'EGFR', ligandId: 'sotorasib', score: 45, agentId: 'agent-5', bindingEnergy: -5.40, keyResidues: ['Met793', 'Cys797'], affinityKd: '180 nM', explainIdx: 1 },
];

const agents = [
  { id: 'agent-1', name: 'Agent Alpha-7', specialty: 'Receptor Tyrosine Kinase Binding', delay: 3000 },
  { id: 'agent-2', name: 'Agent Beta-3', specialty: 'GTPase & Growth Factor Interactions', delay: 5000 },
  { id: 'agent-3', name: 'Agent Gamma-9', specialty: 'Kinase Selectivity Profiling', delay: 7000 },
  { id: 'agent-4', name: 'Agent Delta-2', specialty: 'Cross-Target Validation', delay: 9000 },
  { id: 'agent-5', name: 'Agent Epsilon-5', specialty: 'Off-Target Binding Analysis', delay: 11000 },
];

export function getProtein(id) {
  return proteins.find(p => p.id === id);
}

export function getLigand(id) {
  return ligands.find(l => l.id === id);
}

export function getPair(id) {
  return pairs.find(p => p.id === id);
}

export function getPairsForAgent(agentId) {
  return pairs.filter(p => p.agentId === agentId);
}

export function getExplanation(pair) {
  const protein = getProtein(pair.proteinId);
  const ligand = getLigand(pair.ligandId);
  return explanations[pair.explainIdx](protein, ligand, pair.score);
}

export function getRankedPairs() {
  return [...pairs].sort((a, b) => b.score - a.score);
}

export function getScoreColor(score) {
  if (score >= 70) return 'var(--color-score-high)';
  if (score >= 40) return 'var(--color-score-mid)';
  return 'var(--color-score-low)';
}

export function getScoreLabel(score) {
  if (score >= 70) return 'High';
  if (score >= 40) return 'Moderate';
  return 'Low';
}

export { proteins, ligands, pairs, agents };
