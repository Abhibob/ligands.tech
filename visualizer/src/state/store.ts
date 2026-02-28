import { create } from 'zustand';
import type { FileEntry, Representation, ColorScheme } from '../types/index.ts';
import type { GninaPose } from '../types/gnina.ts';
import type { BoltzConfidence, BoltzAffinity } from '../types/boltz.ts';
import type { PlipInteraction, InteractionType } from '../types/plip.ts';
import type { ProteinResolution, LigandProperties } from '../types/resolution.ts';

interface AppState {
  // Files
  files: FileEntry[];
  addFile: (file: FileEntry) => void;
  removeFile: (id: string) => void;
  clearFiles: () => void;

  // Viewer settings
  representation: Representation;
  setRepresentation: (rep: Representation) => void;
  colorScheme: ColorScheme;
  setColorScheme: (scheme: ColorScheme) => void;
  showSurface: boolean;
  toggleSurface: () => void;

  // gnina poses
  gninaPoses: GninaPose[];
  setGninaPoses: (poses: GninaPose[]) => void;
  activePoseIndex: number;
  setActivePose: (index: number) => void;

  // Boltz confidence
  boltzConfidence: BoltzConfidence | null;
  setBoltzConfidence: (conf: BoltzConfidence | null) => void;
  boltzAffinity: BoltzAffinity | null;
  setBoltzAffinity: (aff: BoltzAffinity | null) => void;

  // PAE
  paeMatrix: number[][] | null;
  setPaeMatrix: (matrix: number[][] | null) => void;

  // PLIP interactions
  plipInteractions: PlipInteraction[];
  setPlipInteractions: (interactions: PlipInteraction[]) => void;
  visibleInteractionTypes: Record<InteractionType, boolean>;
  toggleInteractionType: (type: InteractionType) => void;

  // Protein resolution
  proteinResolution: ProteinResolution | null;
  setProteinResolution: (res: ProteinResolution | null) => void;

  // Ligand properties
  ligandProperties: LigandProperties | null;
  setLigandProperties: (props: LigandProperties | null) => void;

  // Loading state
  isLoading: boolean;
  setLoading: (loading: boolean) => void;
  error: string | null;
  setError: (error: string | null) => void;
}

let fileCounter = 0;

export const useStore = create<AppState>((set) => ({
  files: [],
  addFile: (file) => set((s) => ({ files: [...s.files, file] })),
  removeFile: (id) => set((s) => ({ files: s.files.filter(f => f.id !== id) })),
  clearFiles: () => set({
    files: [],
    gninaPoses: [],
    activePoseIndex: 0,
    boltzConfidence: null,
    boltzAffinity: null,
    paeMatrix: null,
    plipInteractions: [],
    proteinResolution: null,
    ligandProperties: null,
  }),

  representation: 'cartoon',
  setRepresentation: (representation) => set({ representation }),
  colorScheme: 'chain-id',
  setColorScheme: (colorScheme) => set({ colorScheme }),
  showSurface: false,
  toggleSurface: () => set((s) => ({ showSurface: !s.showSurface })),

  gninaPoses: [],
  setGninaPoses: (gninaPoses) => set({ gninaPoses }),
  activePoseIndex: 0,
  setActivePose: (activePoseIndex) => set({ activePoseIndex }),

  boltzConfidence: null,
  setBoltzConfidence: (boltzConfidence) => set({ boltzConfidence }),
  boltzAffinity: null,
  setBoltzAffinity: (boltzAffinity) => set({ boltzAffinity }),

  paeMatrix: null,
  setPaeMatrix: (paeMatrix) => set({ paeMatrix }),

  plipInteractions: [],
  setPlipInteractions: (plipInteractions) => set({ plipInteractions }),
  visibleInteractionTypes: {
    hydrogen_bond: true,
    hydrophobic: true,
    pi_stacking: true,
    salt_bridge: true,
    water_bridge: true,
    halogen_bond: true,
    metal_complex: true,
  },
  toggleInteractionType: (type) => set((s) => ({
    visibleInteractionTypes: {
      ...s.visibleInteractionTypes,
      [type]: !s.visibleInteractionTypes[type],
    },
  })),

  proteinResolution: null,
  setProteinResolution: (proteinResolution) => set({ proteinResolution }),
  ligandProperties: null,
  setLigandProperties: (ligandProperties) => set({ ligandProperties }),

  isLoading: false,
  setLoading: (isLoading) => set({ isLoading }),
  error: null,
  setError: (error) => set({ error }),
}));

export function generateFileId(): string {
  return `file-${Date.now()}-${++fileCounter}`;
}
