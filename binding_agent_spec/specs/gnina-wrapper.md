# `bind-gnina` CLI Spec

## Purpose

Stable wrapper for gnina docking, scoring, and minimization.

## Subcommands

- `dock`
- `score`
- `minimize`
- `doctor`
- `schema`

## Shared direct flags

### Inputs
- `--receptor <pdb|pdbqt>`
- `--ligand <sdf|mol2|pdbqt>` (repeatable or multi-entry)
- `--ligand-table <csv|jsonl>`

### Search space
- `--autobox-ligand <file>`
- `--center-x <float> --center-y <float> --center-z <float>`
- `--size-x <float> --size-y <float> --size-z <float>`

### Execution
- `--cnn-scoring none|rescore|refinement|all`
- `--num-modes <int>`
- `--exhaustiveness <int>`
- `--seed <int>`
- `--cpu <int>`
- `--device <string>`
- `--no-gpu`

### Output and analysis
- `--pose-sort-order cnnscore|cnnaffinity|energy`
- `--atom-terms`
- `--atom-term-data`
- `--log <path>`

## `dock`
Generate independent poses and scores.

Additional flags:
- `--scoring vina|vinardo|ad4_scoring`
- `--out <path>`

## `score`
Score a provided pose without generating new ones.

Behavior:
- implies upstream `--score_only`
- requires `--receptor` and `--ligand`

## `minimize`
Locally optimize a provided pose.

Behavior:
- implies upstream `--minimize`
- may reuse search box only when required by the underlying tool / receptor preparation

Additional flags:
- `--minimize-iters <int>`

## Required normalized result fields

- `summary.mode`
- `summary.numPoses`
- `summary.topPose.rank`
- `summary.topPose.energyKcalMol`
- `summary.topPose.cnnPoseScore`
- `summary.topPose.cnnAffinity`
- `summary.poseSortOrder`
- `artifacts.outputPoseFile`
- `artifacts.logFile`

## Interpretation rules

- Docking energy, CNN pose score, and CNN affinity are different signals.
- Do not compress them into one synthetic score.
- For orthogonal confirmation of a Boltz pose, prefer `score` or `minimize`.
- Use `dock` when you want a truly independent pose proposal.
