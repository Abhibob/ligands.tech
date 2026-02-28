---
name: qmd-search
description: Retrieve the smallest relevant set of local Markdown files for the current task. Use when you need skills, specs, schemas, examples, or notes from the local repository. Prefer this before loading long documents into context.
argument-hint: "[what you need to find, such as a tool skill, schema, or example]"
user-invokable: true
---

# QMD Search

## Purpose
Find the right local files without loading the entire repository into context.

## Use this skill when
- you need a tool skill
- you need a CLI spec
- you need a request/result schema
- you need example YAML or JSON
- you need project notes or past workflow templates

## Typical commands
```bash
bind-qmd query --text "Boltz request schema" --kind schema --top-k 5 --json-out /tmp/qmd.json
bind-qmd query --text "gnina minimize skill" --kind skill --top-k 5 --json-out /tmp/qmd.json
bind-qmd query --text "PLIP example request yaml" --kind example --top-k 5 --json-out /tmp/qmd.json
```

## Retrieval policy
1. Start with the specific tool name.
2. Add the artifact type:
   - skill
   - spec
   - schema
   - example
3. Load the smallest file set that unblocks action.
4. Prefer exact specs over prose notes.

## For broad tasks
Load in this order:
1. `skills/binding-orchestrator/SKILL.md`
2. relevant tool skill
3. relevant wrapper spec
4. relevant request/result schema
5. example files

## Output handling
Keep:
- path
- type
- short snippet
- line span if available

Do not paste huge files into context if a smaller relevant snippet is enough.
