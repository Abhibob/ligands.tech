# Binding Agent Spec Pack

This repo defines a house standard for a CLI-first binding-analysis agent that uses:

- Boltz-2 for pose and affinity hypothesis generation
- PoseBusters for physical plausibility checks
- gnina for independent docking, scoring, and minimization
- PLIP for interaction interpretation
- QMD for local retrieval of skills, schemas, examples, and project notes

The design goal is stability for agents:
- wrap unstable upstream CLIs behind stable wrapper contracts
- accept either flags or structured request files
- emit normalized JSON/YAML result envelopes
- keep native upstream artifacts for debugging and provenance
- make skills queryable by QMD with minimal context loading

## Recommended layout

```text
AGENTS.md
prompts/
skills/
specs/
schemas/
examples/
```

## Wrapper command names

- `bind-boltz`
- `bind-posebusters`
- `bind-gnina`
- `bind-plip`
- `bind-qmd` (optional house wrapper for retrieval)

Each wrapper:
- supports `--request <yaml|json>`
- supports explicit flags for the most common paths
- emits `--json-out`
- may optionally emit `--yaml-out`
- writes upstream artifacts into `--artifacts-dir`

## Canonical interop conventions

- Proteins / complexes: prefer `.pdb` or `.cif`
- Ligands / poses: prefer `.sdf`
- Batch manifests: `.csv` or `.jsonl`
- Primary machine-readable outputs: normalized JSON envelopes
- Optional human-auditable outputs: YAML mirrors of the JSON envelope

## Versioning

All request/result documents use:

- `apiVersion: binding.dev/v1`
- a concrete `kind`
- `metadata.requestId`
- `metadata.createdAt`

Breaking changes should increment the API version.
