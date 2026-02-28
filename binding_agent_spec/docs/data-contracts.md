# Data Contracts and Interop Rules

## 1. Canonical file types

- protein target: FASTA, PDB, or CIF
- ligand library: SDF preferred
- complex for interaction profiling: PDB preferred
- request documents: YAML preferred for humans, JSON also supported
- result documents: JSON required, YAML optional

## 2. Ligand identity contract

Each ligand should have:
- `id`
- at least one of:
  - `smiles`
  - `sdfPath`
  - `mol2Path`

## 3. Path semantics

All paths in request/result files should be:
- relative to the request file location, or
- absolute

Wrappers should normalize and store resolved absolute paths in `inputsResolved`.

## 4. Artifact retention

Wrappers must preserve:
- generated upstream inputs
- native tool outputs
- stdout and stderr logs when useful
- normalized result envelopes

## 5. Batch semantics

When a request contains many ligands:
- preserve ligand order
- assign stable ligand IDs
- store per-ligand result records
- record skipped and failed ligands separately

## 6. Confidence semantics

Confidence is a narrative field, not a tool-native numeric field.
It should be computed by the orchestrator, not silently invented inside single-tool wrappers.
