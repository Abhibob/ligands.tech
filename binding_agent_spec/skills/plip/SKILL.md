---
name: plip
description: Use the stable PLIP wrapper to profile noncovalent interactions in a protein-ligand complex. Use when you need a residue-level explanation of why a pose may be plausible, want to compare contact patterns across ligands, or need machine-readable interaction summaries plus optional text, XML, image, or PyMOL outputs.
argument-hint: "[complex file or PDB id, optional binding-site id, optional output modes]"
user-invokable: true
---

# PLIP Wrapper Skill

## Purpose
Explain a pose in interaction terms.

## Use this skill when
- you already have a candidate complex
- you want residue-level interpretation
- you want text/XML/PyMOL/image artifacts for review

## Command patterns

### Single complex profiling
```bash
bind-plip profile \
  --complex complex.pdb \
  --json-out /tmp/plip.json
```

### Batch profile a directory of complexes
```bash
bind-plip profile \
  --complex-dir boltz/ \
  --top-n 10 \
  --json-out /tmp/plip-batch.json
```
`--complex-dir` globs all PDB/CIF files in the directory. Results are sorted by total interaction count. `--top-n N` limits output to top N (max 100). Writes a `MANIFEST_plip.md`.

## Interpretation policy
PLIP is explanatory.
It helps answer:
- which residues contact the ligand?
- what interaction types appear?
- how does ligand A differ from ligand B?

It does not prove binding by itself.

## Useful outputs
- interaction counts by type
- interacting residues
- optional XML, text, images, and PyMOL session
