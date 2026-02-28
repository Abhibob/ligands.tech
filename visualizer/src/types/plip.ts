export interface Coord3D {
  x: number;
  y: number;
  z: number;
}

export type InteractionType =
  | 'hydrogen_bond'
  | 'hydrophobic'
  | 'pi_stacking'
  | 'salt_bridge'
  | 'water_bridge'
  | 'halogen_bond'
  | 'metal_complex';

export interface PlipInteraction {
  type: InteractionType;
  proteinCoord: Coord3D;
  ligandCoord: Coord3D;
  residueName: string;
  residueNumber: number;
  chain: string;
  distance: number;
}
