---
name: gnina
description: Use the stable gnina wrapper for independent docking, rescoring, and local minimization. Use when you need an orthogonal signal to a Boltz pose, want to score a supplied pose, refine a pose locally, or generate independent poses in a defined binding site.
argument-hint: "[receptor, ligand(s), mode: dock, score, or minimize, and box definition]"
user-invokable: true
---

# gnina Wrapper Skill

## Purpose
Provide an orthogonal docking/scoring/minimization signal.

## Choose the right subcommand
- `score`: check a provided pose
- `minimize`: locally refine a provided pose
- `dock`: generate independent poses

## Search space policy
Prefer `--autobox-ligand` when a reference ligand or known binder is available.
Otherwise specify an explicit box.

## Command patterns
### Score a provided pose
```bash
bind-gnina score \
  --receptor receptor.pdb \
  --ligand pose.sdf \
  --autobox-ligand pose.sdf \
  --cnn-scoring rescore \
  --json-out /tmp/gnina.json
```

### Minimize a provided pose
```bash
bind-gnina minimize \
  --receptor receptor.pdb \
  --ligand pose.sdf \
  --cnn-scoring rescore \
  --json-out /tmp/gnina.json
```

### Dock independently
```bash
bind-gnina dock \
  --receptor receptor.pdb \
  --ligand ligands.sdf \
  --autobox-ligand ref.sdf \
  --cnn-scoring rescore \
  --num-modes 9 \
  --json-out /tmp/gnina.json
```

## Interpretation
Do not collapse:
- docking energy
- CNN pose score
- CNN affinity
into one fake score.

Use gnina as orthogonal evidence, especially after Boltz.
