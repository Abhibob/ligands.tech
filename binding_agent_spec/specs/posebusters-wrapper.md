# `bind-posebusters` CLI Spec

## Purpose

Stable wrapper for PoseBusters plausibility checking of generated or docked poses.

## Subcommands

- `check`
- `doctor`
- `schema`

## `check` synopsis

```bash
bind-posebusters check \
  (--request REQUEST.yaml | [direct flags]) \
  --json-out result.json
```

## Direct flags

### Inputs
- `--pred <sdf>` (repeatable)
- `--protein <pdb|cif>`
- `--reference-ligand <sdf>`
- `--table <csv|jsonl>`: batch table with paths

### Config
- `--config auto|mol|dock|redock`
- `--top-n <int>`
- `--full-report`

### Performance
- `--max-workers <int>`
- `--chunk-size <int>`

## Wrapper behavior

1. Resolve input mode:
   - `mol` for molecule-only plausibility
   - `dock` for pose conditioned on protein
   - `redock` for predicted vs true ligand against protein
2. Run PoseBusters.
3. Convert the report into:
   - a concise pass/fail summary
   - categorized failures
   - optional detailed metrics

## Required normalized result fields

Per pose:
- `passesAllChecks`
- `passFraction`
- `fatalFailures[]`
- `majorFailures[]`
- `minorFailures[]`
- `failedChecks[]`
- `rawOutputPath`
- `fullMetrics` when `--full-report` is used

## Categorization policy

The wrapper should map raw PoseBusters checks into:
- fatal: sanitization, disconnected atoms, impossible geometry, severe clashes
- major: bond / angle failures, protein overlap, severe volume overlap
- minor: less critical formatting or non-blocking warnings

## Interpretation rules

- Any fatal failure should set downstream confidence to low unless the user explicitly asked for debugging.
- A pass does not prove binding; it only says the pose is not obviously implausible by the tested rules.
