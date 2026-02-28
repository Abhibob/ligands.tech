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

## Command pattern
```bash
bind-plip profile \
  --request examples/requests/plip_profile.yaml \
  --json-out /tmp/plip.json
```

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
