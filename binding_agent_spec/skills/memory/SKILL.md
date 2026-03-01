---
name: memory
description: Shared semantic memory for binding agents. Store, search, and profile findings across agents in a run. Uses Supermemory API when SUPERMEMORY_API_KEY is set, otherwise falls back to local Markdown files with keyword search.
argument-hint: "[subcommand: add, search, profile, doctor, schema]"
user-invokable: false
---

# bind-memory Wrapper Skill

## Purpose
Shared memory layer that lets agents store and retrieve findings across a run.
Pipeline results (resolve, boltz, gnina, posebusters, plip) are auto-stored
after each step. Agents can also store and search for extra context.

## Backends
- **Supermemory** (hosted): Set `SUPERMEMORY_API_KEY` env var. Provides semantic
  search, entity extraction, and profile generation.
- **Local fallback**: No API key needed. Stores `.md` files in
  `<workspace>/memory/<tag>/findings/`. Keyword-based search only.

## Command patterns

### Store a finding
```bash
bind-memory add \
  --content "Boltz: erlotinib binds EGFR, binder_prob=0.92" \
  --tag run-20260301-a1b2c3 \
  --custom-id boltz-findings-erlotinib \
  --metadata '{"tool":"boltz","target":"EGFR","binder_probability":0.92}' \
  --json-out results/memory-add.json
```

### Search for findings
```bash
bind-memory search \
  --query "EGFR docking results" \
  --tag run-20260301-a1b2c3 \
  --limit 5 \
  --json-out results/memory-search.json
```

### Generate a run profile
```bash
bind-memory profile \
  --tag run-20260301-a1b2c3 \
  --query "binding evidence" \
  --json-out results/memory-profile.json
```

### Check backend status
```bash
bind-memory doctor
```

## When to use
- **search**: Before starting work, to see what other agents found. When
  synthesizing a final answer across subagents. When a subagent needs file
  paths from the parent's resolve step.
- **add**: To store extra context beyond auto-stored pipeline results (e.g.,
  research notes, literature findings, cross-agent conclusions).
- **profile**: To generate a synthesized overview of all findings in a run,
  useful before writing the final answer.

## When NOT to use
- Don't store large files — store summaries with file paths instead.
- Don't search memory for data you just produced — read the result JSON directly.
- Don't use memory as a replacement for the checklist tool — they serve different
  purposes (checklist tracks pipeline progress, memory stores semantic findings).

## Output fields

### add
Returns: `id` (document ID), `path` (local) or API response, `backend`.

### search
Returns: `results[]` (each with `id`, `content`, `score`), `total`, `backend`.

### profile
Returns: `profile` (text summary), `num_documents`, `backend`.

## Auto-store behavior
Pipeline tool results are automatically stored in shared memory after each
successful command. This includes:
- **resolve**: protein name, PDB/FASTA/SDF paths
- **boltz**: binder probability, affinity, confidence, complex path
- **gnina**: CNN score, affinity, energy, output SDF path
- **posebusters**: pass rate, failures
- **plip**: interaction counts, key residues

Auto-stores are best-effort, non-blocking, and idempotent (using custom_id).
