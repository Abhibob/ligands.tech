---
name: websearch
description: Search the web for scientific literature, drug discovery information, protein targets, and research papers using the Exa API. Use when you need background knowledge, recent publications, mechanism of action details, clinical trial data, or any information not available from the local CLI tools.
argument-hint: "[search query, optional category filter, optional domain filter]"
user-invokable: true
---

# Web Search Skill

## Purpose
Search the web for scientific and drug discovery information to inform binding analysis decisions.

## When to use
- Before starting analysis, to understand a disease/target/drug
- To find mechanism of action, known binding sites, selectivity profiles
- To discover recent research on a protein target or drug class
- To find clinical trial results or approved drug information
- When the user asks an open-ended research question
- To validate or contextualize computational results

## When NOT to use
- When you need to resolve a specific protein/ligand (use bind-resolve instead)
- When you need structural data (use bind-resolve search for PDB structures)
- For actual docking or prediction (use bind-gnina, bind-boltz)

## Command patterns

### Basic search
```bash
bind-websearch "EGFR inhibitor mechanism of action" --json-out results/search.json
```

### Search for research papers
```bash
bind-websearch "kinase drug resistance mechanisms" \
  --category "research paper" \
  --num-results 5 \
  --json-out results/search.json
```

### Search specific domains
```bash
bind-websearch "TP53 drug targets" \
  --include-domain pubmed.ncbi.nlm.nih.gov \
  --include-domain nature.com \
  --json-out results/search.json
```

### Search for news/clinical updates
```bash
bind-websearch "EGFR inhibitor clinical trial 2025" \
  --category news \
  --num-results 5 \
  --json-out results/search.json
```

## Output fields
- `summary.results[]`: Array of search results
  - `title`: Result title
  - `url`: Source URL
  - `text`: Extracted page text (up to --max-chars)
  - `highlights`: Key relevant passages
  - `published_date`: Publication date

## Environment
Requires `EXA_API_KEY` environment variable set.

## Typical workflow
1. `bind-websearch` to research the target/disease → read results
2. `bind-resolve protein` → resolve the identified target
3. Continue with docking/prediction pipeline
