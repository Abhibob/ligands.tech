---
name: binding-orchestrator
description: Plan and execute end-to-end protein-ligand binding workflows using stable wrappers for Boltz-2, PoseBusters, gnina, and PLIP. Use when the user gives a natural-language task that spans multiple tools, asks whether something binds, requests a screening workflow, or wants a cross-tool interpretation.
argument-hint: "[goal, target, ligands, files, and stage such as screening or optimization]"
user-invokable: true
---

# Binding Orchestrator

## Use this skill when
- the task spans more than one tool
- the user asks for a full workflow
- the stage is screening, shortlist triage, or lead optimization
- the user wants an integrated interpretation instead of a raw tool run

## Do not use this skill when
- the user explicitly asks for one tool only and does not want orchestration
- the task is just local retrieval; use the QMD skill first

## Default plan
1. Identify the stage: screening, optimization, or explanation.
2. Resolve inputs into stable request files.
3. Run Boltz-2 first when a pose or affinity hypothesis is needed.
4. Run PoseBusters on generated or supplied poses.
5. Run gnina for orthogonal scoring, minimization, or independent docking.
6. Run PLIP on the final candidate pose.
7. Summarize agreement, disagreement, and confidence.

## Evidence policy
Never claim that one computation verifies binding.
Report:
- Boltz hypothesis
- PoseBusters plausibility
- gnina orthogonal signal
- PLIP interaction rationale
- final confidence

## Stage-aware metric policy
### Screening
Prefer the Boltz screening-oriented output and triage aggressively.

### Optimization
Prefer relative ranking among likely binders and compare contact differences.

### Explanation
Prefer PLIP plus a pose-quality narrative.

## Files to retrieve when needed
- `specs/common-cli.md`
- `specs/boltz2-wrapper.md`
- `specs/posebusters-wrapper.md`
- `specs/gnina-wrapper.md`
- `specs/plip-wrapper.md`
- matching request/result schemas
- relevant examples

## Output checklist
- goal
- resolved inputs
- commands or request files
- per-tool outputs
- disagreement analysis
- confidence
- next step
