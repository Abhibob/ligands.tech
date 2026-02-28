// AlphaFold/Boltz pLDDT color scale
export function plddtColor(plddt: number): string {
  if (plddt > 90) return '#0053D6'; // dark blue — very high confidence
  if (plddt > 70) return '#65CBF3'; // light blue — high confidence
  if (plddt > 50) return '#FFDB13'; // yellow — low confidence
  return '#FF7D45';                  // orange — very low confidence
}

// PLIP interaction type colors
export const INTERACTION_COLORS: Record<string, string> = {
  hydrogen_bond: '#2196F3',   // blue
  hydrophobic: '#FFC107',     // yellow
  pi_stacking: '#4CAF50',     // green
  salt_bridge: '#F44336',     // red
  water_bridge: '#00BCD4',    // cyan
  halogen_bond: '#9C27B0',    // purple
  metal_complex: '#795548',   // brown
};

// gnina CNNscore color
export function cnnScoreColor(score: number): string {
  if (score > 0.8) return '#4CAF50'; // green
  if (score > 0.5) return '#FFC107'; // yellow
  return '#F44336';                   // red
}

// Generate distinct colors for multiple ligands
const LIGAND_PALETTE = [
  '#00C853', '#FF6D00', '#AA00FF', '#00B8D4',
  '#DD2C00', '#6200EA', '#00BFA5', '#FFD600',
];

export function ligandColor(index: number): string {
  return LIGAND_PALETTE[index % LIGAND_PALETTE.length];
}
