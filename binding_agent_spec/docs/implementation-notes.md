# Implementation Notes

## Why wrappers instead of raw CLIs

Upstream tools differ in:
- input style
- output format
- naming conventions
- log verbosity
- assumptions about search boxes, templates, and artifact paths

Stable wrappers make them usable by agents.

## Why request files

Natural-language tasks often mention:
- many ligands
- optional protein files
- search-space hints
- stage-specific goals
- output preferences

A request file is easier for the agent to validate, diff, store, and rerun than a giant flag string.

## Why JSON result envelopes

Agents should not parse free-form terminal text unless debugging.
A normalized JSON envelope avoids brittle scraping and makes downstream reasoning more reliable.

## Why a house QMD wrapper

The skill ecosystem is converging on SKILL.md, but local retrieval stacks vary.
A house retrieval wrapper keeps the agent interface stable even if the underlying search implementation changes.
