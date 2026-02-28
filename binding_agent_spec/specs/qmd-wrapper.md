# `bind-qmd` CLI Spec

## Purpose

Optional house wrapper for local retrieval over Markdown skills, specs, schemas, notes, and examples.

## Why a house wrapper exists

QMD is an emerging pattern rather than one universal spec. Different teams use:
- raw `qmd` CLI
- custom retrieval daemons
- vector stores over Markdown
- hybrid BM25 + vector + rerank stacks

This wrapper makes retrieval stable for the agent.

## Subcommands

- `query`
- `get`
- `update`
- `doctor`
- `schema`

## `query` synopsis

```bash
bind-qmd query \
  (--request REQUEST.yaml | --text "query") \
  --json-out result.json
```

## Direct flags

- `--text <string>`
- `--collection <name>` (repeatable)
- `--strategy keyword|semantic|hybrid`
- `--top-k <int>`
- `--paths-only`
- `--full`
- `--line-numbers`
- `--rerank`
- `--tag <tag>` (repeatable)
- `--kind skill|spec|schema|example|note|any`
- `--must-include <glob>` (repeatable)
- `--must-exclude <glob>` (repeatable)

## Required normalized result fields

- `summary.queryText`
- `summary.strategyUsed`
- `summary.results[]`
  - `path`
  - `title`
  - `kind`
  - `score`
  - `snippet`
  - `lineStart`
  - `lineEnd`
  - `tags[]`

## Interpretation rules

- Use retrieval to load only the files needed for the current task.
- Prefer the orchestrator skill first for broad tasks.
- For tool-specific tasks, load the tool skill, CLI spec, and request/result schemas.
