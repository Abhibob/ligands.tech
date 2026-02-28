# `bind-plip` CLI Spec

## Purpose

Stable wrapper for PLIP interaction profiling on a final or candidate complex.

## Subcommands

- `profile`
- `doctor`
- `schema`

## `profile` synopsis

```bash
bind-plip profile \
  (--request REQUEST.yaml | [direct flags]) \
  --json-out result.json
```

## Direct flags

### Inputs
- `--complex <pdb>`
- `--pdb-id <id>`
- `--binding-site <bsid>`
- `--model <int>`

### Output toggles
- `--txt`
- `--xml`
- `--pymol`
- `--pics`

### Structure handling
- `--chains <csv>`
- `--residues <spec>`
- `--peptides <spec>`
- `--intra <spec>`
- `--nohydro`
- `--keepmod`
- `--nofix`

## Wrapper behavior

1. Validate that one complex or PDB ID is provided.
2. Run PLIP with requested output types.
3. Parse interaction sets into a normalized interaction model.
4. Emit counts, residue summaries, and file paths.

## Required normalized result fields

- `summary.bindingSites[]`
- `summary.selectedBindingSite`
- `summary.interactionCounts`
- `summary.interactingResidues[]`
- `summary.interactionsByType`
- `artifacts.txtReport`
- `artifacts.xmlReport`
- `artifacts.pymolSession`
- `artifacts.images[]`

## Interpretation rules

- Use PLIP to explain why a pose may be plausible.
- Do not use PLIP as a standalone claim that binding is real.
- Residue-level contact differences are especially useful for SAR discussions.
