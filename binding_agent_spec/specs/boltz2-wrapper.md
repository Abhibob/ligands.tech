# `bind-boltz` CLI Spec

## Purpose

Stable wrapper around Boltz-2 inference for protein-ligand structure and affinity hypothesis generation.

## Subcommands

- `predict`
- `doctor`
- `schema`

## `predict` synopsis

```bash
bind-boltz predict \
  (--request REQUEST.yaml | [direct flags]) \
  --json-out result.json \
  [--yaml-out result.yaml] \
  [--artifacts-dir artifacts/]
```

## Direct flags

### Core inputs
- `--protein-fasta <file>`
- `--protein-sequence <string>`
- `--protein-pdb <file>`
- `--protein-cif <file>`
- `--ligand-sdf <file>` (repeatable)
- `--ligand-smiles <string>` (repeatable)
- `--ligand-table <csv|jsonl>` (columns defined in the schema)
- `--task structure|affinity|both`

### MSA / templates
- `--use-msa-server`
- `--msa-dir <dir>`
- `--template <file>` (repeatable)

### Controllability / constraints
- `--constraint-file <yaml|json>`
- `--pocket-residue <chain:resid>` (repeatable)
- `--contact <ligandAtomSpec=residueSpec>` (repeatable)
- `--method-conditioning <string>` (repeatable)

### Execution
- `--top-k <int>`
- `--rank-by binder-probability|affinity-value`
- `--seed <int>`
- `--recycling-steps <int>`
- `--diffusion-samples <int>`
- `--cache-dir <dir>`

### Debug / provenance
- `--emit-upstream-input <path>`: write the generated Boltz YAML
- `--ingest-upstream-output <dir>`: normalize an already completed Boltz run
- `--keep-temp`

## Wrapper behavior

1. Validate request against the house schema.
2. Convert normalized request into upstream Boltz YAML when needed.
3. Execute Boltz.
4. Parse the native outputs.
5. Emit a normalized result envelope.

## Required normalized result fields

- `summary.primaryComplexPath`
- `summary.primaryConfidenceJsonPath`
- `summary.affinity.binderProbability`
- `summary.affinity.affinityValue`
- `summary.affinity.affinityUnit`
- `summary.rankMetricUsed`
- `artifacts.upstreamInputYaml`
- `artifacts.nativeOutputDir`
- `artifacts.modelFiles[]`
- `warnings[]`

## Interpretation rules

- For screening, use `binderProbability`.
- For optimization among likely binders, use `affinityValue`.
- A strong affinity signal without plausibility checks is not enough for a high-confidence claim.
