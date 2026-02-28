---
name: boltz2
description: Use the stable Boltz-2 wrapper to generate protein-ligand pose and affinity hypotheses. Use when the task asks what a bound complex may look like, whether a ligand is likely to be a binder, or how a series of ligands should be ranked for screening or optimization.
argument-hint: "[protein, ligands, stage, and whether you need structure, affinity, or both]"
user-invokable: true
---

# Boltz-2 Wrapper Skill

## Purpose
Predict a protein-ligand complex and affinity-related outputs using the stable `bind-boltz` wrapper.

## When to use
- screening or hit discovery
- pose generation for a candidate ligand
- optimization-oriented ranking among likely binders
- creating a starting pose for downstream checks

## When not to use
- as the only evidence for binding
- when the user only wants interaction profiling on an existing complex; use PLIP
- when the main question is physical plausibility; use PoseBusters

## Command patterns
### Structured request
```bash
bind-boltz predict --request examples/requests/boltz_predict_single.yaml --json-out /tmp/boltz.json
```

### Direct flags
```bash
bind-boltz predict \
  --protein-fasta target.fasta \
  --ligand-sdf ligands.sdf \
  --task both \
  --use-msa-server \
  --rank-by binder-probability \
  --json-out /tmp/boltz.json
```

## Interpretation
- screening: read `summary.affinity.binderProbability`
- optimization: read `summary.affinity.affinityValue`
- always preserve the generated pose artifact path for downstream tools

## Next step
Normally run PoseBusters on the chosen Boltz pose before drawing conclusions.
