import type { PlipInteraction, InteractionType, Coord3D } from '../types/plip.ts';

export function parsePlipXml(xmlText: string): PlipInteraction[] {
  const parser = new DOMParser();
  const doc = parser.parseFromString(xmlText, 'text/xml');
  const interactions: PlipInteraction[] = [];

  const bindingSites = doc.querySelectorAll('bindingsite');
  for (const site of bindingSites) {
    interactions.push(...parseHydrogenBonds(site));
    interactions.push(...parseHydrophobic(site));
    interactions.push(...parsePiStacking(site));
    interactions.push(...parseSaltBridges(site));
    interactions.push(...parseWaterBridges(site));
    interactions.push(...parseHalogenBonds(site));
    interactions.push(...parseMetalComplexes(site));
  }

  return interactions;
}

function parseHydrogenBonds(site: Element): PlipInteraction[] {
  return parseInteractionGroup(site, 'hydrogen_bonds', 'hydrogen_bond', (el) => ({
    proteinCoord: parseCoord(el, 'protcoo'),
    ligandCoord: parseCoord(el, 'ligcoo'),
    distance: parseFloat(el.querySelector('dist_d-a')?.textContent ?? '0'),
  }));
}

function parseHydrophobic(site: Element): PlipInteraction[] {
  return parseInteractionGroup(site, 'hydrophobic_interactions', 'hydrophobic_interaction', (el) => ({
    proteinCoord: parseCoord(el, 'protcoo'),
    ligandCoord: parseCoord(el, 'ligcoo'),
    distance: parseFloat(el.querySelector('dist')?.textContent ?? '0'),
  }));
}

function parsePiStacking(site: Element): PlipInteraction[] {
  return parseInteractionGroup(site, 'pi_stacks', 'pi_stack', (el) => ({
    proteinCoord: parseCoord(el, 'protcoo'),
    ligandCoord: parseCoord(el, 'ligcoo'),
    distance: parseFloat(el.querySelector('centdist')?.textContent ?? '0'),
  }));
}

function parseSaltBridges(site: Element): PlipInteraction[] {
  return parseInteractionGroup(site, 'salt_bridges', 'salt_bridge', (el) => ({
    proteinCoord: parseCoord(el, 'protcoo'),
    ligandCoord: parseCoord(el, 'ligcoo'),
    distance: parseFloat(el.querySelector('dist')?.textContent ?? '0'),
  }));
}

function parseWaterBridges(site: Element): PlipInteraction[] {
  return parseInteractionGroup(site, 'water_bridges', 'water_bridge', (el) => ({
    proteinCoord: parseCoord(el, 'protcoo'),
    ligandCoord: parseCoord(el, 'ligcoo'),
    distance: parseFloat(el.querySelector('dist_d-a')?.textContent ?? '0'),
  }));
}

function parseHalogenBonds(site: Element): PlipInteraction[] {
  return parseInteractionGroup(site, 'halogen_bonds', 'halogen_bond', (el) => ({
    proteinCoord: parseCoord(el, 'protcoo'),
    ligandCoord: parseCoord(el, 'ligcoo'),
    distance: parseFloat(el.querySelector('dist')?.textContent ?? '0'),
  }));
}

function parseMetalComplexes(site: Element): PlipInteraction[] {
  return parseInteractionGroup(site, 'metal_complexes', 'metal_complex', (el) => ({
    proteinCoord: parseCoord(el, 'metalcoo'),
    ligandCoord: parseCoord(el, 'targetcoo'),
    distance: parseFloat(el.querySelector('dist')?.textContent ?? '0'),
  }));
}

function parseInteractionGroup(
  site: Element,
  groupTag: string,
  itemTag: string,
  extractCoords: (el: Element) => { proteinCoord: Coord3D; ligandCoord: Coord3D; distance: number },
): PlipInteraction[] {
  const type = groupTag.replace(/_interactions|_bonds|_stacks|_bridges|_complexes|s$/g, '') as InteractionType;
  const items = site.querySelectorAll(`${groupTag} > ${itemTag}`);
  const results: PlipInteraction[] = [];

  for (const el of items) {
    const { proteinCoord, ligandCoord, distance } = extractCoords(el);
    results.push({
      type,
      proteinCoord,
      ligandCoord,
      residueName: el.querySelector('restype')?.textContent ?? '',
      residueNumber: parseInt(el.querySelector('resnr')?.textContent ?? '0', 10),
      chain: el.querySelector('reschain')?.textContent ?? 'A',
      distance,
    });
  }

  return results;
}

function parseCoord(el: Element, tag: string): Coord3D {
  const coordEl = el.querySelector(tag);
  return {
    x: parseFloat(coordEl?.querySelector('x')?.textContent ?? '0'),
    y: parseFloat(coordEl?.querySelector('y')?.textContent ?? '0'),
    z: parseFloat(coordEl?.querySelector('z')?.textContent ?? '0'),
  };
}
