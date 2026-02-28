import { proteins } from "./proteins";
import { ligands } from "./ligands";
import { pairs } from "./pairs";
import { researchers } from "./researchers";
export { getExplanation, getDetailedExplanation } from "./explanations";

export { proteins, ligands, pairs, researchers };

export function getProtein(id: string) {
  return proteins.find((p) => p.id === id)!;
}

export function getLigand(id: string) {
  return ligands.find((l) => l.id === id)!;
}

export function getPair(id: string) {
  return pairs.find((p) => p.id === id);
}

export function getResearcher(id: string) {
  return researchers.find((r) => r.id === id);
}

export function getPairsByResearcher(researcherId: string) {
  return pairs.filter((p) => p.researcherId === researcherId);
}
