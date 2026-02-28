import type { PluginUIContext } from 'molstar/lib/mol-plugin-ui/context';
import { setSubtreeVisibility } from 'molstar/lib/mol-plugin/behavior/static/state';
import type { MolFormat } from '../types/index.ts';

type MolstarFormat = 'pdb' | 'mmcif' | 'sdf' | 'mol2' | 'mol' | 'xyz' | 'pdbqt';

const FORMAT_MAP: Partial<Record<MolFormat, MolstarFormat>> = {
  pdb: 'pdb',
  mmcif: 'mmcif',
  sdf: 'sdf',
  mol2: 'mol2',
  pdbqt: 'pdb', // PDBQT is close enough to PDB for coordinate parsing
  xyz: 'xyz',
};

export interface LoadedStructure {
  label: string;
  dataRef: string;
  visible: boolean;
}

export function getMolstarFormat(format: MolFormat): MolstarFormat | null {
  return FORMAT_MAP[format] ?? null;
}

export async function loadStructureData(
  plugin: PluginUIContext,
  content: string | ArrayBuffer,
  format: MolFormat,
  label: string,
  preset: string = 'default',
): Promise<LoadedStructure | null> {
  const molFormat = getMolstarFormat(format);
  if (!molFormat) return null;

  const isBinary = format === 'bcif';

  const rawData = isBinary
    ? new Uint8Array(content as ArrayBuffer)
    : content as string;

  const data = await plugin.builders.data.rawData(
    { data: rawData as string, label },
    { state: { isGhost: true } },
  );

  const trajectory = await plugin.builders.structure.parseTrajectory(
    data,
    isBinary ? 'mmcif' : molFormat,
  );
  await plugin.builders.structure.hierarchy.applyPreset(trajectory, preset as 'default');

  return {
    label,
    dataRef: data.ref,
    visible: true,
  };
}

export async function loadBcifData(
  plugin: PluginUIContext,
  buffer: ArrayBuffer,
  label: string,
): Promise<LoadedStructure | null> {
  const data = await plugin.builders.data.rawData(
    { data: new Uint8Array(buffer), label },
    { state: { isGhost: true } },
  );
  const trajectory = await plugin.builders.structure.parseTrajectory(data, 'mmcif');
  await plugin.builders.structure.hierarchy.applyPreset(trajectory, 'default');

  return {
    label,
    dataRef: data.ref,
    visible: true,
  };
}

export function toggleVisibility(
  plugin: PluginUIContext,
  structure: LoadedStructure,
  visible: boolean,
) {
  structure.visible = visible;
  setSubtreeVisibility(plugin.state.data, structure.dataRef, !visible);
}

export async function clearAll(plugin: PluginUIContext) {
  await plugin.clear();
}

export async function removeAllRepresentations(plugin: PluginUIContext) {
  const structures = plugin.managers.structure.hierarchy.current.structures;
  for (const s of structures) {
    for (const c of s.components) {
      await plugin.managers.structure.component.removeRepresentations([c]);
    }
  }
}

export type RepresentationType =
  | 'cartoon'
  | 'ball-and-stick'
  | 'spacefill'
  | 'molecular-surface'
  | 'gaussian-surface'
  | 'line'
  | 'backbone';

export async function setRepresentationType(
  plugin: PluginUIContext,
  repType: RepresentationType,
) {
  const structures = plugin.managers.structure.hierarchy.current.structures;
  for (const structure of structures) {
    // Remove existing representations
    for (const component of structure.components) {
      await plugin.managers.structure.component.removeRepresentations([component]);
      await plugin.managers.structure.component.addRepresentation(
        [component],
        repType,
      );
    }
  }
}
