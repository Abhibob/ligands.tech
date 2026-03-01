# Visualizer File Formats

## Individual formats

| Format | Extension(s) | Contains | Source |
|--------|-------------|----------|--------|
| PDB | `.pdb` | Protein/complex 3D coords (legacy) | RCSB, PDBe, AlphaFold, ESMFold |
| mmCIF | `.cif`, `.mmcif` | Protein/complex 3D coords (modern) | RCSB, PDBe, AlphaFold, Boltz output |
| BinaryCIF | `.bcif` | Protein/complex 3D coords (binary, compact) | RCSB ModelServer, AlphaFold |
| SDF / MOL | `.sdf`, `.mol` | Ligand/small molecule 3D/2D coords + properties | PubChem, ChEMBL, RCSB CCD, RDKit, gnina output |
| MOL2 | `.mol2` | Ligand with atom types + charges | gnina, PLIP |
| PDBQT | `.pdbqt` | Protein or ligand with partial charges + torsion tree | gnina/AutoDock input/output |
| SMILES | `.smi`, inline string | Ligand 1D representation (no coords) | PubChem, ChEMBL, user input |
| FASTA | `.fasta`, `.fa` | Protein/DNA/RNA sequence (no coords) | UniProt, user input |
| XYZ | `.xyz` | Generic 3D atomic coords | QM tools |
| PQR | `.pqr` | Protein coords + charge + radius (electrostatics) | APBS |
| MAP / DX | `.map`, `.dx`, `.cube` | Volumetric / electron density / electrostatic potential | CCP4, APBS |
| PAE JSON | `.json` | Predicted Aligned Error matrix | AlphaFold, Boltz confidence output |
| Confidence JSON | `.json` | pLDDT, pTM, ipTM scores | Boltz output |
| PSE | `.pse` | PyMOL session | PLIP output |
| XML | `.xml` | PLIP interaction report | PLIP output |

## Pairs that should be visualized together

| Pair | Protein format | Ligand/other format | Use case |
|------|---------------|---------------------|----------|
| **Protein + docked ligand** | `.pdb` / `.cif` | `.sdf` | View gnina dock/score/minimize result |
| **Protein + predicted complex** | `.cif` (from Boltz) | Ligand already inside the CIF | View Boltz prediction |
| **Protein + multiple poses** | `.pdb` | multi-model `.sdf` | Compare docking poses (gnina `--num-modes 9`) |
| **Protein + interaction overlay** | `.pdb` | PLIP `.xml` or `.pse` | Show H-bonds, hydrophobic contacts, pi-stacking |
| **Protein + reference ligand + docked ligand** | `.pdb` | two `.sdf` files | Compare redocked vs crystal pose |
| **Protein + electron density** | `.pdb` / `.cif` | `.map` / `.ccp4` | Validate experimental fit |
| **Protein + electrostatic surface** | `.pdb` / `.pqr` | `.dx` / `.cube` | Show charge distribution in binding site |
| **Protein + PAE heatmap** | `.cif` | PAE `.json` | Assess prediction confidence (AlphaFold/Boltz) |
| **Protein + pLDDT coloring** | `.cif` (B-factor = pLDDT) | — | Color by per-residue confidence |
| **Ligand 2D + ligand 3D** | — | 2D `.sdf` + 3D `.sdf` | Side-by-side structure vs conformer |
| **Multiple ligands overlaid** | `.pdb` (shared receptor) | multiple `.sdf` | SAR comparison, pose overlay |
| **Sequence + structure** | `.fasta` | `.pdb` / `.cif` | Sequence-structure alignment view |

## gnina output specifically

gnina writes a multi-model SDF where each model is a ranked pose. SD properties per pose:

| SD property | Type | Meaning |
|-------------|------|---------|
| `minimizedAffinity` | float | Vina score (kcal/mol, more negative = better) |
| `CNNscore` | float 0-1 | Probability pose is correct |
| `CNNaffinity` | float | Predicted pK binding affinity |
| `CNN_VS` | float | CNNscore * CNNaffinity (composite) |

Visualizer should: load all poses, let user toggle between them, show scores in a sidebar table.

## Boltz output specifically

Boltz writes a single CIF with protein + ligand together. Companion files:

| File | What to visualize |
|------|-------------------|
| `*_model_0.cif` | 3D structure (color by pLDDT in B-factor column) |
| `confidence_*_model_0.json` | pTM, ipTM, pLDDT stats → show as badges/numbers |
| `affinity_*.json` | Binder probability + affinity value → show as badges |
| `pae_*_model_0.npz` | PAE matrix → render as 2D heatmap beside structure |

## PLIP output specifically

| File | What to visualize |
|------|-------------------|
| `*_proflip.pdb` | Preprocessed complex |
| `*.xml` | Parse interaction types → render as dashed lines / surfaces on structure |
| `*.pse` | Open in PyMOL (or parse for interaction geometry) |
| `*.png` / `*.svg` | Static 2D interaction diagram |
