---
name: resolve
description: Unified molecule resolution tool. Resolves protein targets (UniProt, PDB structures, binding sites), ligands (PubChem, CCD, SMILES), known binders (ChEMBL approved drugs and bioactivity), and searches RCSB PDB for experimental structures. Use this as the single entry point before docking or analysis.
argument-hint: "[protein name or ligand name, subcommand: protein, ligand, binders, or search]"
user-invokable: true
---

# bind-resolve Wrapper Skill

## Purpose
Single entry point for resolving all molecular identifiers needed before
docking or binding analysis: proteins, ligands, known binders, and PDB structures.

## Choose the right subcommand
- `protein`: resolve a gene name or UniProt accession → UniProt data, ranked PDB structures, binding sites, FASTA
- `ligand`: resolve a compound by name, SMILES, CCD code, or PubChem CID → SMILES, properties, SDF files
- `binders`: find approved drugs and active compounds for a protein target via ChEMBL
- `search`: search RCSB PDB for experimental structures by gene name

## Important notes
- `bind-resolve` is not installed as a CLI entry point. Run it as: `python -m bind_tools.resolve.cli`
- Organism names use **common names** (human, mouse, rat), not scientific names
- Run `doctor` to verify all dependencies and API connectivity

## Command patterns

### Resolve a protein target
```bash
python -m bind_tools.resolve.cli protein \
  --name EGFR \
  --organism human \
  --download-dir /tmp/workspace \
  --json-out /tmp/protein.json
```

### Resolve by UniProt accession (skip search)
```bash
python -m bind_tools.resolve.cli protein \
  --uniprot P00533 \
  --json-out /tmp/protein.json
```

### Resolve a ligand by name
```bash
python -m bind_tools.resolve.cli ligand \
  --name imatinib \
  --download-dir /tmp/workspace \
  --json-out /tmp/ligand.json
```

### Resolve a ligand by SMILES
```bash
python -m bind_tools.resolve.cli ligand \
  --smiles "C#Cc1cccc(Nc2ncnc3cc(OCCOC)c(OCCOC)cc23)c1" \
  --download-dir /tmp/workspace \
  --json-out /tmp/ligand.json
```

### Resolve a ligand by CCD code (RCSB Ligand Expo ideal SDF)
```bash
python -m bind_tools.resolve.cli ligand \
  --ccd ATP \
  --download-dir /tmp/workspace \
  --json-out /tmp/ligand.json
```

### Resolve a ligand by PubChem CID
```bash
python -m bind_tools.resolve.cli ligand \
  --pubchem-cid 176870 \
  --download-dir /tmp/workspace \
  --json-out /tmp/ligand.json
```

### Find known binders for a target
```bash
python -m bind_tools.resolve.cli binders \
  --gene EGFR \
  --organism human \
  --min-pchembl 6.0 \
  --limit 20 \
  --json-out /tmp/binders.json
```

### Search RCSB PDB for structures
```bash
python -m bind_tools.resolve.cli search \
  --gene TP53 \
  --organism human \
  --limit 10 \
  --json-out /tmp/search.json
```

### Check dependencies
```bash
python -m bind_tools.resolve.cli doctor
```

## Output fields

### protein
Returns: `uniprot_accession`, `gene_name`, `protein_name`, `organism`,
`sequence_length`, `fasta_path`, `best_structures` (ranked by ligand-bound > X-ray > resolution),
`binding_sites` (ligand IDs and names from PDB), `downloaded_path`, `num_structures`.

### ligand
Returns: `name`, `smiles`, `iupac_name`, `molecular_formula`, `molecular_weight`,
`logp`, `tpsa`, `h_bond_donors`, `h_bond_acceptors`, `rotatable_bonds`,
`pubchem_cid`, `inchi_key`, `synonyms`, `sdf_path`.

### binders
Returns: `uniprot_accession`, `chembl_target_id`, `target_name`,
`approved_drugs` (name, mechanism, action, phase),
`top_compounds` (ChEMBL ID, pChEMBL, SMILES).

### search
Returns: `query`, `total_count`, `pdb_ids`.

## Typical workflow
1. `resolve protein` → get UniProt ID, best PDB structure, binding sites
2. `resolve ligand` → get SMILES and SDF for the compound of interest
3. `resolve binders` → find known drugs/actives for comparison
4. Feed results into `bind-gnina dock` or `bind-boltz predict`
