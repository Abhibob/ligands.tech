# BindingOps Architecture

> A multi-agent system for computational protein-ligand binding analysis.
> This document covers the full stack: CLI tool wrappers, agent orchestration, subagent management, shared memory, and the LLM backend.

---

## 1. System Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                        USER / CALLER                                │
│            (natural language task or structured request)             │
└──────────────────────────────┬──────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    ORCHESTRATOR AGENT                                │
│  ┌───────────┐  ┌──────────────────┐  ┌──────────────────────────┐ │
│  │  Planner   │  │  Tool Dispatcher  │  │  Consensus Interpreter  │ │
│  └───────────┘  └──────────────────┘  └──────────────────────────┘ │
│                         │                                           │
│            ┌────────────┼────────────┐                              │
│            ▼            ▼            ▼                              │
│    ┌──────────┐  ┌──────────┐  ┌──────────┐   GENERAL-PURPOSE     │
│    │ Subagent │  │ Subagent │  │ Subagent │   SUBAGENT POOL       │
│    │  (any    │  │  (any    │  │  (any    │   (model's discretion) │
│    │   task)  │  │   task)  │  │   task)  │                        │
│    └────┬─────┘  └────┬─────┘  └────┬─────┘                        │
│         │             │             │                               │
│         ▼             ▼             ▼                               │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │          SUPERMEMORY (api.supermemory.ai)                    │   │
│  │  ┌─────────────┐  ┌──────────────┐  ┌───────────────────┐  │   │
│  │  │  Documents   │  │   Memories    │  │    Profiles       │  │   │
│  │  │  (raw JSON,  │  │  (extracted   │  │  (aggregated      │  │   │
│  │  │   Markdown)  │  │   facts)      │  │   run state)      │  │   │
│  │  └─────────────┘  └──────────────┘  └───────────────────┘  │   │
│  │            ↕ semantic search + metadata filters              │   │
│  │  Fallback: local workspace/{run-id}/*.md files              │   │
│  └─────────────────────────────────────────────────────────────┘   │
└──────────────────────────────┬──────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│                       CLI TOOL LAYER                                │
│  ┌───────────┐ ┌───────────┐ ┌───────────────┐ ┌──────┐ ┌─────┐  │
│  │bind-boltz │ │bind-gnina │ │bind-posebusters│ │bind- │ │bind-│  │
│  │           │ │  (Docker) │ │               │ │plip  │ │qmd  │  │
│  └─────┬─────┘ └─────┬─────┘ └──────┬────────┘ └──┬───┘ └──┬──┘  │
│        │             │              │              │        │      │
│        ▼             ▼              ▼              ▼        ▼      │
│   boltz CLI    gnina binary   posebusters API   PLIP API   glob   │
│   (subprocess)  (in container)  (Python)        (Python)  +regex  │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 2. CLI Tool Layer

### 2.1 Package Layout

Single installable Python package: `bind-tools`

```
src/bind_tools/
├── common/              # shared infrastructure
│   ├── envelope.py      # Pydantic base models (apiVersion, kind, metadata)
│   ├── cli_base.py      # reusable Typer options/callbacks
│   ├── runner.py        # subprocess + Docker execution helpers
│   └── errors.py        # exit codes (0,2,3,4,5,6,7), error hierarchy
├── boltz/               # bind-boltz
│   ├── cli.py           # Typer app: predict | doctor | schema
│   ├── models.py        # BoltzPredictRequest, BoltzPredictResult
│   └── runner.py        # request → boltz YAML → subprocess → parse outputs
├── gnina/               # bind-gnina
│   ├── cli.py           # Typer app: dock | score | minimize | doctor | schema
│   ├── models.py        # GninaDockRequest, GninaScoreRequest, GninaMinimizeRequest, GninaResult
│   └── runner.py        # request → docker run gnina/gnina → parse SDF with RDKit
├── posebusters/         # bind-posebusters
│   ├── cli.py           # Typer app: check | doctor | schema
│   ├── models.py        # PoseBustersCheckRequest, PoseBustersCheckResult
│   └── runner.py        # request → PoseBusters(config).bust() → categorize failures
├── plip/                # bind-plip
│   ├── cli.py           # Typer app: profile | doctor | schema
│   ├── models.py        # PlipProfileRequest, PlipProfileResult
│   └── runner.py        # request → PDBComplex.analyze() → extract interactions
└── qmd/                 # bind-qmd
    ├── cli.py           # Typer app: query | get | update | doctor | schema
    ├── models.py        # QmdQueryRequest, QmdQueryResult
    └── runner.py        # keyword/glob search over local Markdown/JSON/YAML
```

### 2.2 Common CLI Contract

Every wrapper supports three invocation styles:

```bash
# 1. Structured request file
bind-boltz predict --request req.yaml --json-out result.json

# 2. Direct flags
bind-boltz predict --protein-fasta target.fasta --ligand-smiles "CCO" --json-out result.json

# 3. Stdin JSON
cat req.json | bind-boltz predict --stdin-json --json-out result.json
```

All wrappers share these flags:

| Flag | Purpose |
|------|---------|
| `--request <path>` | YAML/JSON request document |
| `--stdin-json` | Read request from stdin |
| `--json-out <path>` | Write normalized JSON result envelope |
| `--yaml-out <path>` | Optional YAML mirror |
| `--artifacts-dir <dir>` | Upstream native artifacts |
| `--run-id <string>` | Caller-supplied identifier |
| `--device <string>` | `cuda:0`, `cpu`, etc. Auto-detects by default |
| `--timeout-s <int>` | Hard timeout |
| `--dry-run` | Validate + print plan, don't execute |
| `--verbose` / `--quiet` | Log verbosity |

### 2.3 Normalized Result Envelope

Every tool emits a JSON document with this shape:

```json
{
  "apiVersion": "binding.dev/v1",
  "kind": "BoltzPredictResult",
  "metadata": {
    "requestId": "req-001",
    "createdAt": "2026-02-27T12:00:00Z"
  },
  "tool": "boltz",
  "toolVersion": "1.0.0",
  "wrapperVersion": "0.1.0",
  "status": "succeeded | failed | partial",
  "inputsResolved": { },
  "parametersResolved": { },
  "summary": { },
  "artifacts": { },
  "warnings": [],
  "errors": [],
  "provenance": { },
  "runtimeSeconds": 42.5
}
```

### 2.4 Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Success |
| 2 | Validation error (bad request) |
| 3 | Input missing or unreadable |
| 4 | Upstream tool execution failure |
| 5 | Timeout |
| 6 | Partial success with warnings |
| 7 | Unsupported request combination |

### 2.5 GPU / CUDA Policy

- `--device` flag on every wrapper; default: auto-detect via `torch.cuda.is_available()`
- Global override: `BIND_TOOLS_DEVICE` environment variable
- gnina (Docker): `--gpus all` when device is CUDA, omitted when `cpu`
- boltz: `--accelerator gpu` / `--accelerator cpu`
- posebusters / plip / qmd: CPU-only (no GPU needed)

### 2.6 Tool Details

#### bind-boltz
- **Upstream**: `boltz predict` CLI (subprocess)
- **Input**: FASTA/PDB/CIF protein + SDF/SMILES ligands
- **Output**: CIF structure, confidence JSON (pLDDT, pTM, ipTM), affinity JSON (binder probability, affinity value)
- **Key fields**: `summary.affinity.binderProbability` (screening), `summary.affinity.affinityValue` (optimization)

#### bind-gnina
- **Upstream**: `gnina` binary via Docker (`gnina/gnina:latest`)
- **Modes**: `dock` (pose generation), `score` (evaluate existing pose), `minimize` (local refinement)
- **Input**: PDB receptor + SDF/MOL2 ligand(s) + search space definition
- **Output**: Ranked poses with `minimizedAffinity` (kcal/mol), `CNNscore` (0-1), `CNNaffinity` (pK)
- **SDF parsing**: RDKit `SDMolSupplier` extracts SD properties

#### bind-posebusters
- **Upstream**: `posebusters` Python API (direct import, no subprocess)
- **Input**: Predicted pose SDF + optional protein PDB + optional reference ligand
- **Output**: Per-pose pass/fail with categorized failures (fatal/major/minor)
- **Failure categories**:
  - Fatal: sanitization, disconnected atoms, impossible geometry
  - Major: bond/angle failures, protein overlap
  - Minor: non-blocking warnings

#### bind-plip
- **Upstream**: `plip` Python API (`PDBComplex.analyze()`)
- **Input**: PDB complex file or PDB ID
- **Output**: Interaction counts by type, interacting residues, per-type details
- **Interaction types**: H-bonds, hydrophobic, pi-stacking, pi-cation, salt bridges, water bridges, halogen bonds, metal complexes
- **Optional artifacts**: TXT report, XML, PyMOL session, images

#### bind-qmd
- **Upstream**: Local filesystem (no external tool)
- **Strategy**: keyword matching + glob patterns over Markdown/JSON/YAML files
- **Input**: Query text + optional filters (kind, collection, tags)
- **Output**: Ranked file matches with path, title, snippet, score

---

## 3. Agent Orchestration Layer

### 3.1 Subagent Philosophy

Subagents are **general-purpose LLM agents**, not rigid single-tool executors. The orchestrator spawns subagents for any reason it sees fit:

- Run a specific tool and interpret its output
- Divide a large task into parallel chunks (e.g., batch screening)
- Research a sub-question (e.g., "what pocket residues matter for CDK2?")
- Compare results across multiple prior runs
- Prepare or clean input files

The model decides at runtime what tools a subagent needs, what context to load, and what to write back to shared memory. There are no hardcoded "Boltz subagent" or "gnina subagent" classes — a subagent receives a task in natural language, a system prompt with available tools, and uses discretion.

### 3.2 Agent Roles (Conventions, Not Types)

These are **recommended role hints**, not enforced types. The orchestrator can assign any role string, or none at all.

| Role Hint | Typical Use | Tools Likely Used |
|-----------|-------------|-------------------|
| `tool-runner` | Execute a single bind-* command and interpret output | `run_cli`, `memory_write` |
| `batch-worker` | Process a chunk of a parallelized workload | `run_cli`, `memory_write` |
| `researcher` | Investigate a sub-question, search context | `run_cli` (bind-qmd), `memory_read`, `memory_search` |
| `analyst` | Compare results, synthesize findings | `memory_read`, `memory_search`, `memory_write` |
| `prep` | Generate or validate input files | `run_cli`, `memory_write` |
| *(any string)* | Orchestrator's discretion — arbitrary tasks | All tools available |

### 3.3 Subagent Lifecycle

```
┌──────────┐     spawn()      ┌───────────┐
│Orchestrator├───────────────►│ Subagent   │
│          │                  │ (pending)  │
└──────────┘                  └─────┬──────┘
                                    │ run()
                                    ▼
                              ┌───────────┐
                              │ Subagent   │
                              │ (running)  │──── reads/writes Supermemory
                              └─────┬──────┘
                                    │ complete() / fail()
                                    ▼
                              ┌───────────┐
                              │ Subagent   │
                              │ (done)     │──── result in Supermemory
                              └────────────┘
```

States: `pending` → `running` → `done` | `failed` | `cancelled`

### 3.4 Subagent Spawn Interface

Each subagent is an LLM chat completion call (via OpenRouter) with tool access. The orchestrator spawns them via a `spawn_subagent` tool call:

```json
{
  "type": "function",
  "function": {
    "name": "spawn_subagent",
    "description": "Launch a subagent to handle a task. Subagents are general-purpose LLM agents that receive a natural language task and a set of tools. Use for parallelizing work, dividing large tasks, or delegating sub-problems. The model uses its own discretion about what to keep in context and what to offload to Supermemory.",
    "parameters": {
      "type": "object",
      "properties": {
        "agent_id": {
          "type": "string",
          "description": "Unique identifier for this subagent instance"
        },
        "task": {
          "type": "string",
          "description": "Natural language task description. Be specific about what the subagent should do, what inputs to use, and where to write results."
        },
        "role": {
          "type": "string",
          "description": "Optional role hint (e.g., 'tool-runner', 'batch-worker', 'researcher', 'analyst'). Informational only — does not restrict the subagent's capabilities."
        },
        "system_prompt_extra": {
          "type": "string",
          "description": "Optional additional system prompt content appended to the base subagent prompt. Use for task-specific instructions or constraints."
        },
        "inputs": {
          "type": "object",
          "description": "Structured inputs (file paths, parameters, config) passed to the subagent as context"
        },
        "tools": {
          "type": "array",
          "items": { "type": "string" },
          "description": "Optional tool whitelist. If omitted, subagent gets all tools. Use to restrict scope when appropriate.",
          "default": ["run_cli", "memory_add", "memory_search", "memory_read", "memory_profile"]
        },
        "model": {
          "type": "string",
          "description": "OpenRouter model ID. Defaults to haiku for cheap/fast subagents. Use sonnet for complex reasoning tasks.",
          "default": "anthropic/claude-haiku-4-5"
        },
        "container_tag": {
          "type": "string",
          "description": "Supermemory container tag for scoping this agent's memory. Typically the run ID."
        },
        "depends_on": {
          "type": "array",
          "items": { "type": "string" },
          "description": "Agent IDs that must complete before this one starts"
        },
        "parallel_group": {
          "type": "string",
          "description": "Optional group ID — agents in the same group run concurrently"
        },
        "max_turns": {
          "type": "integer",
          "description": "Maximum LLM round-trips before the subagent is forced to return. Prevents runaway agents.",
          "default": 10
        }
      },
      "required": ["agent_id", "task"]
    }
  }
}
```

### 3.5 Context Management — Model Discretion

Subagents decide what to keep in their conversation context vs. what to offload to Supermemory. Guidelines baked into the subagent system prompt:

- **Keep in context**: the current task, active tool results being interpreted, small intermediate state
- **Write to Supermemory**: completed findings, large result payloads, artifact paths, anything another agent might need
- **Search Supermemory**: when you need context from a prior step, another agent's findings, or historical run data — don't assume it's in your context window

This means subagents are **not** given the full history of every prior agent. They start with their task + system prompt, and pull what they need from Supermemory on demand.

### 3.6 Parallel Execution Patterns

#### Pattern 1: Batch parallelism (screening)

```
Orchestrator receives: "Screen these 50 ligands against EGFR"
    │
    ├─► spawn_subagent(task="Run bind-boltz predict on ligands 1-10, write
    │     results to Supermemory with tag 'screen-batch'", parallel_group="screen")
    ├─► spawn_subagent(task="...ligands 11-20...", parallel_group="screen")
    ├─► spawn_subagent(task="...ligands 21-30...", parallel_group="screen")
    ├─► spawn_subagent(task="...ligands 31-40...", parallel_group="screen")
    └─► spawn_subagent(task="...ligands 41-50...", parallel_group="screen")
    │
    │  (all complete)
    │
    ├─► spawn_subagent(task="Search Supermemory for all screen-batch results,
    │     rank by binder probability, run bind-posebusters on top 10")
    ├─► spawn_subagent(task="Run bind-gnina score on top 10 hits from screening")
    │
    └─► Orchestrator reads findings, synthesizes consensus
```

#### Pattern 2: Pipeline parallelism (orthogonal tools)

```
After boltz completes:
    ├─► spawn_subagent(task="Run posebusters check on boltz pose")  ← parallel
    └─► spawn_subagent(task="Run gnina score on boltz pose")        ← parallel
```

#### Pattern 3: Research + execution split

```
Orchestrator receives: "What are good drug candidates for CDK2?"
    │
    ├─► spawn_subagent(role="researcher", task="Search Supermemory and
    │     bind-qmd for CDK2 binding site info, known inhibitors, pocket residues.
    │     Write a research summary to Supermemory.")
    │
    │  (researcher completes)
    │
    ├─► spawn_subagent(task="Using the CDK2 research in Supermemory, generate
    │     SMILES for 10 candidate ligands and prepare a boltz request file")
    ...
```

#### Pattern 4: General work division

```
Orchestrator receives a complex multi-part question:
    │
    ├─► spawn_subagent(task="Part 1: Analyze the EGFR binding results...")
    ├─► spawn_subagent(task="Part 2: Compare with historical CDK2 runs...")
    └─► spawn_subagent(task="Part 3: Summarize SAR trends across the series...")
```

---

## 4. Supermemory: Shared Agent Memory

### 4.1 Overview

Shared state between agents is powered by **[Supermemory](https://supermemory.ai)** — a hosted memory and context API purpose-built for AI agents. Supermemory provides semantic search, automatic memory extraction, and user/project profiles across all subagents in a run.

**Why Supermemory (not just files)**:
- Semantic search across all agent findings (sub-300ms recall)
- Automatic relationship tracking between memories (updates, extends, derives)
- Metadata filtering for scoping (by run ID, tool, stage, etc.)
- Handles all content types (text, JSON, Markdown, PDFs, images)
- No self-hosted vector DB infrastructure needed
- Local Markdown files remain as a **fallback** for offline/air-gapped environments

### 4.2 Architecture

```
┌────────────────────────────────────────────────────────────┐
│                    SUPERMEMORY (hosted)                      │
│                  api.supermemory.ai                          │
│                                                              │
│  ┌─────────────────────────────────────────────────────┐    │
│  │  Container: run-{id}                                 │    │
│  │                                                       │    │
│  │  Documents (raw ingested content):                    │    │
│  │    - tool result envelopes (JSON)                     │    │
│  │    - execution plans (Markdown)                       │    │
│  │    - research notes                                   │    │
│  │                                                       │    │
│  │  Memories (extracted semantic facts):                  │    │
│  │    - "EGFR + erlotinib: binder_prob=0.92"            │    │
│  │    - "PoseBusters: pose passes all checks"           │    │
│  │    - "gnina CNNscore=0.85, CNNaffinity=-7.2"         │    │
│  │    - "PLIP: 3 H-bonds to hinge region"              │    │
│  │                                                       │    │
│  │  Relationships:                                       │    │
│  │    posebusters result ──extends──► boltz result       │    │
│  │    gnina rescore ──extends──► boltz pose              │    │
│  │    round-2 affinity ──updates──► round-1 affinity     │    │
│  └─────────────────────────────────────────────────────┘    │
│                                                              │
│  ┌─────────────────────────────────────────────────────┐    │
│  │  Profile: run-{id}                                   │    │
│  │    static:  ["target: EGFR", "stage: screening"]     │    │
│  │    dynamic: ["top hit: erlotinib (0.92)", ...]        │    │
│  └─────────────────────────────────────────────────────┘    │
└────────────────────────────────────────────────────────────┘
```

### 4.3 Supermemory API Integration

**Base URL**: `https://api.supermemory.ai`
**Auth**: `Authorization: Bearer $SUPERMEMORY_API_KEY`

#### 4.3.1 Add a document (agent writes findings)

```
POST /v3/documents
```

```json
{
  "content": "# Boltz Findings\n\n## Key Results\n- binder probability: 0.92\n- affinity: -7.2 kcal/mol\n- pose: /workspace/run-001/artifacts/boltz/model_0.cif\n\n## Interpretation\nHigh-probability binder. Pose places ligand in ATP pocket near A:745, A:793.",
  "containerTag": "run-20260227-001",
  "customId": "boltz-findings-ligand-a",
  "metadata": {
    "tool": "boltz",
    "stage": "screening",
    "target": "EGFR",
    "ligand_id": "ligand_a",
    "binder_probability": 0.92,
    "affinity_value": -7.2
  },
  "entityContext": "This is a Boltz-2 prediction result for protein-ligand binding analysis. Extract key metrics (binder probability, affinity value), the target protein, ligand identifier, and any warnings about the prediction quality."
}
```

Response:
```json
{
  "id": "doc_abc123",
  "status": "queued"
}
```

#### 4.3.2 Search across all agent findings

```
POST /v4/search
```

```json
{
  "q": "EGFR binder probability results",
  "containerTag": "run-20260227-001",
  "searchMode": "hybrid",
  "limit": 10,
  "threshold": 0.5,
  "rerank": true,
  "filters": {
    "AND": [
      { "key": "tool", "value": "boltz" },
      { "filterType": "numeric", "key": "binder_probability", "value": "0.7", "numericOperator": ">=" }
    ]
  }
}
```

Response:
```json
{
  "results": [
    {
      "id": "doc_abc123",
      "memory": "EGFR + ligand_a: binder probability 0.92, affinity -7.2 kcal/mol. High-probability binder, pose in ATP pocket.",
      "chunk": "# Boltz Findings\n\n## Key Results\n- binder probability: 0.92...",
      "similarity": 0.94,
      "metadata": { "tool": "boltz", "binder_probability": 0.92 },
      "updatedAt": "2026-02-27T12:05:00Z",
      "version": 1
    }
  ],
  "timing": 47,
  "total": 1
}
```

#### 4.3.3 Get run profile (aggregated context)

```
POST /v4/profile
```

```json
{
  "containerTag": "run-20260227-001",
  "q": "binding analysis progress"
}
```

Response:
```json
{
  "profile": {
    "static": [
      "Target: EGFR kinase domain",
      "Stage: screening",
      "Ligand library: 50 compounds"
    ],
    "dynamic": [
      "Boltz screening complete: 8/50 ligands show binder_prob > 0.7",
      "Top hit: ligand_a (binder_prob=0.92)",
      "PoseBusters: 6/8 shortlisted poses pass all checks",
      "gnina rescoring in progress"
    ]
  },
  "searchResults": {
    "results": [...],
    "total": 12,
    "timing": 52
  }
}
```

### 4.4 Agent Memory Tools (exposed to LLM agents)

These are the tool definitions given to every subagent for Supermemory interaction:

```json
{
  "name": "memory_add",
  "description": "Store a finding, result, or note in shared Supermemory. Other agents can search for it later. Use this to record tool outputs, intermediate results, research findings, or any context that should persist beyond your conversation.",
  "parameters": {
    "type": "object",
    "properties": {
      "content": {
        "type": "string",
        "description": "The content to store. Markdown preferred. Include key metrics, file paths, and your interpretation."
      },
      "container_tag": {
        "type": "string",
        "description": "Scope tag, typically the run ID (e.g., 'run-20260227-001')"
      },
      "custom_id": {
        "type": "string",
        "description": "Unique ID for this memory (e.g., 'boltz-findings-ligand-a'). Using the same custom_id again will update the existing memory."
      },
      "metadata": {
        "type": "object",
        "description": "Key-value metadata for filtering. Use for: tool name, stage, target, ligand_id, numeric scores."
      }
    },
    "required": ["content", "container_tag"]
  }
}
```

```json
{
  "name": "memory_search",
  "description": "Search shared Supermemory for findings from other agents, prior results, or any stored context. Use this instead of assuming context is in your conversation — other agents' work is only accessible through Supermemory.",
  "parameters": {
    "type": "object",
    "properties": {
      "query": {
        "type": "string",
        "description": "Natural language search query"
      },
      "container_tag": {
        "type": "string",
        "description": "Scope to a specific run or project"
      },
      "filters": {
        "type": "object",
        "description": "Metadata filters. Supports AND/OR with keys: tool, stage, target, ligand_id, and numeric comparisons on scores."
      },
      "limit": {
        "type": "integer",
        "default": 10
      },
      "search_mode": {
        "type": "string",
        "enum": ["hybrid", "memories"],
        "default": "hybrid",
        "description": "'hybrid' searches both extracted memories and raw chunks. 'memories' searches only extracted semantic facts (faster, more concise)."
      }
    },
    "required": ["query"]
  }
}
```

```json
{
  "name": "memory_profile",
  "description": "Get an aggregated profile of a run or project. Returns static facts and dynamic recent context. Use this for a quick overview before diving into specific searches.",
  "parameters": {
    "type": "object",
    "properties": {
      "container_tag": {
        "type": "string",
        "description": "Run or project ID"
      },
      "query": {
        "type": "string",
        "description": "Optional query to also return relevant search results alongside the profile"
      }
    },
    "required": ["container_tag"]
  }
}
```

### 4.5 Local Markdown Fallback

For offline, air-gapped, or self-hosted environments, the system falls back to local Markdown files with the same semantic structure. The `memory_add` / `memory_search` tools detect whether `SUPERMEMORY_API_KEY` is set and route accordingly.

#### Fallback workspace layout

```
workspace/{run-id}/
├── plan.md               # execution plan (written by orchestrator)
├── memory.md             # shared run-level state
├── findings/
│   ├── {agent-id}.md     # each subagent writes its own findings file
│   └── ...
├── artifacts/            # tool output files
│   ├── boltz/
│   ├── gnina/
│   ├── posebusters/
│   └── plip/
├── consensus.md          # orchestrator's final synthesis
└── log.md                # append-only event log
```

#### Fallback search

When Supermemory is unavailable, `memory_search` degrades to:
1. Glob all `.md` and `.json` files in the workspace
2. Keyword match against the query
3. Return file paths + matching line snippets
4. No semantic ranking, no relationship tracking

This is functional but significantly less capable than hosted Supermemory.

### 4.6 Memory Lifecycle Within a Run

```
  Orchestrator spawns run
        │
        ├─► memory_add: execution plan, target info, ligand list
        │
        ├─► Subagent A runs boltz
        │     └─► memory_add: boltz findings + metrics as metadata
        │
        ├─► Subagent B runs posebusters
        │     ├─► memory_search: "boltz pose path for ligand_a"  ← finds A's output
        │     └─► memory_add: posebusters findings
        │
        ├─► Subagent C runs gnina (parallel with B)
        │     ├─► memory_search: "boltz pose and receptor path"  ← finds A's output
        │     └─► memory_add: gnina findings
        │
        ├─► Orchestrator: memory_search for all findings
        │     └─► memory_profile: get aggregated run state
        │
        └─► Orchestrator: memory_add consensus + final answer
```

### 4.7 Cross-Run Memory

Supermemory's container tags enable memory scoping at multiple levels:

| Scope | containerTag pattern | Purpose |
|-------|---------------------|---------|
| Single run | `run-20260227-001` | Isolate findings to one analysis |
| Project | `project-egfr-campaign` | Share findings across runs for the same target |
| Global | `global-knowledge` | Store learned heuristics, tool quirks, common patterns |

Subagents can search across containers when the orchestrator grants cross-scope access.

### 4.8 Concurrency Rules

With Supermemory (hosted):
- **No file-level contention** — each `memory_add` call is an independent document with its own `customId`
- **Reads are always safe** — `memory_search` returns point-in-time results
- **Updates are idempotent** — same `customId` replaces the previous version
- **Relationships are automatic** — Supermemory detects when new content updates or extends existing memories

With local fallback:
- **Findings files**: each subagent writes only its own `{agent-id}.md` (no contention)
- **memory.md**: append-only during execution
- **log.md**: append-only, timestamped
- **plan.md**: written once by orchestrator, read-only after
- **consensus.md**: written only by orchestrator after all subagents complete

---

## 5. LLM Backend: OpenRouter Chat Completions

### 5.1 Why OpenRouter

- Single API for multiple model providers (Anthropic, Google, Meta, etc.)
- Model routing and fallback
- Consistent tool calling interface across providers
- Cost tracking and rate limiting

### 5.2 API Endpoint

```
POST https://openrouter.ai/api/v1/chat/completions
```

### 5.3 Request Headers

```http
Authorization: Bearer $OPENROUTER_API_KEY
Content-Type: application/json
HTTP-Referer: https://bindingops.dev
X-Title: BindingOps Agent
```

### 5.4 Request Body Shape

```json
{
  "model": "anthropic/claude-sonnet-4",
  "messages": [
    {
      "role": "system",
      "content": "You are a BindingOps subagent specialized in..."
    },
    {
      "role": "user",
      "content": "Run Boltz prediction on EGFR with ligand CCO"
    },
    {
      "role": "assistant",
      "content": null,
      "tool_calls": [
        {
          "id": "call_abc123",
          "type": "function",
          "function": {
            "name": "run_cli",
            "arguments": "{\"command\": \"bind-boltz predict ...\"}"
          }
        }
      ]
    },
    {
      "role": "tool",
      "tool_call_id": "call_abc123",
      "content": "{\"status\": \"succeeded\", ...}"
    }
  ],
  "tools": [
    {
      "type": "function",
      "function": {
        "name": "run_cli",
        "description": "Execute a bind-* CLI command and return the JSON result envelope",
        "parameters": {
          "type": "object",
          "properties": {
            "command": {
              "type": "string",
              "description": "Full CLI command to execute"
            },
            "timeout_s": {
              "type": "integer",
              "description": "Timeout in seconds",
              "default": 300
            }
          },
          "required": ["command"]
        }
      }
    },
    {
      "type": "function",
      "function": {
        "name": "spawn_subagent",
        "description": "Launch a subagent for parallel tool execution",
        "parameters": { "...": "see section 3.3" }
      }
    },
    {
      "type": "function",
      "function": {
        "name": "memory_read",
        "description": "Read from shared workspace memory",
        "parameters": { "...": "see section 4.4" }
      }
    },
    {
      "type": "function",
      "function": {
        "name": "memory_write",
        "description": "Write to shared workspace memory",
        "parameters": { "...": "see section 4.4" }
      }
    }
  ],
  "tool_choice": "auto",
  "temperature": 0.1,
  "max_tokens": 4096
}
```

### 5.5 Response Body Shape

```json
{
  "id": "gen-abc123",
  "model": "anthropic/claude-sonnet-4",
  "choices": [
    {
      "index": 0,
      "message": {
        "role": "assistant",
        "content": "I'll run Boltz prediction now.",
        "tool_calls": [
          {
            "id": "call_xyz789",
            "type": "function",
            "function": {
              "name": "run_cli",
              "arguments": "{\"command\": \"bind-boltz predict --protein-fasta egfr.fasta --ligand-smiles CCO --task both --json-out /tmp/boltz.json\"}"
            }
          }
        ]
      },
      "finish_reason": "tool_calls"
    }
  ],
  "usage": {
    "prompt_tokens": 1250,
    "completion_tokens": 89,
    "total_tokens": 1339
  }
}
```

### 5.6 Streaming (SSE)

Add `"stream": true` to the request. Response arrives as Server-Sent Events:

```
data: {"id":"gen-abc","choices":[{"delta":{"role":"assistant","content":"I'll"}}]}
data: {"id":"gen-abc","choices":[{"delta":{"content":" run"}}]}
data: {"id":"gen-abc","choices":[{"delta":{"tool_calls":[{"index":0,"id":"call_1","type":"function","function":{"name":"run_cli","arguments":""}}]}}]}
data: {"id":"gen-abc","choices":[{"delta":{"tool_calls":[{"index":0,"function":{"arguments":"{\"command\":"}}]}}]}
...
data: [DONE]
```

### 5.7 Model Selection by Agent Role

| Agent Role | Recommended Model | Rationale |
|-----------|-------------------|-----------|
| Orchestrator | `anthropic/claude-sonnet-4` | Strong reasoning, tool use, planning |
| Tool Subagent | `anthropic/claude-haiku-4-5` | Fast, cheap, structured tool calls |
| Discovery (batch) | `anthropic/claude-haiku-4-5` | High throughput for parallel screening |
| Consensus Synthesis | `anthropic/claude-sonnet-4` | Nuanced scientific interpretation |
| Fallback | `google/gemini-2.5-flash` | Cost-effective fallback |

---

## 6. Agent Tool Registry

The full set of tools available to agents. Every subagent receives all of these unless the orchestrator restricts via the `tools` whitelist in `spawn_subagent`.

### 6.1 CLI Execution

```json
{
  "name": "run_cli",
  "description": "Execute a bind-* CLI command and return the JSON result envelope. Use for bind-boltz, bind-gnina, bind-posebusters, bind-plip, bind-qmd.",
  "parameters": {
    "type": "object",
    "properties": {
      "command": { "type": "string", "description": "Full CLI command to execute" },
      "timeout_s": { "type": "integer", "default": 300, "description": "Hard timeout in seconds" },
      "capture_stderr": { "type": "boolean", "default": true }
    },
    "required": ["command"]
  }
}
```

### 6.2 Subagent Management

```json
{
  "name": "spawn_subagent",
  "description": "Launch a general-purpose subagent. See section 3.4 for full schema.",
  "parameters": { "...": "see section 3.4" }
}
```

```json
{
  "name": "check_subagent",
  "description": "Check the status of a spawned subagent. Returns: pending, running, done, failed, or cancelled.",
  "parameters": {
    "type": "object",
    "properties": {
      "agent_id": { "type": "string" }
    },
    "required": ["agent_id"]
  }
}
```

```json
{
  "name": "cancel_subagent",
  "description": "Cancel a running subagent. Use when results are no longer needed or the agent is stuck.",
  "parameters": {
    "type": "object",
    "properties": {
      "agent_id": { "type": "string" },
      "reason": { "type": "string" }
    },
    "required": ["agent_id"]
  }
}
```

```json
{
  "name": "wait_for_agents",
  "description": "Block until all specified agents complete or fail. Use after spawning parallel subagents.",
  "parameters": {
    "type": "object",
    "properties": {
      "agent_ids": { "type": "array", "items": { "type": "string" } },
      "timeout_s": { "type": "integer", "default": 600 }
    },
    "required": ["agent_ids"]
  }
}
```

### 6.3 Supermemory Tools

These wrap the Supermemory API (sections 4.3-4.4). When `SUPERMEMORY_API_KEY` is not set, they fall back to local Markdown workspace files.

```json
{
  "name": "memory_add",
  "description": "Store a finding, result, or note in shared Supermemory. Maps to POST /v3/documents.",
  "parameters": { "...": "see section 4.4" }
}
```

```json
{
  "name": "memory_search",
  "description": "Search shared Supermemory for findings from other agents or prior results. Maps to POST /v4/search.",
  "parameters": { "...": "see section 4.4" }
}
```

```json
{
  "name": "memory_profile",
  "description": "Get an aggregated profile of a run or project. Maps to POST /v4/profile.",
  "parameters": { "...": "see section 4.4" }
}
```

---

## 7. Workflow Examples

### 7.1 Single Binding Question

```
User: "Does erlotinib bind EGFR?"

Orchestrator:
  1. memory_add: execution plan (stage=explanation, target=EGFR, ligand=erlotinib)
  2. spawn_subagent(task="Run bind-boltz predict for EGFR + erlotinib.
       Write binder probability, affinity value, and pose path to Supermemory.")
  3. wait_for_agents([boltz-1])
  4. spawn_subagent(task="Search Supermemory for the boltz pose path,
       run bind-posebusters check on it. Write pass/fail to Supermemory.")
     spawn_subagent(task="Search Supermemory for the boltz pose path,
       run bind-gnina score on it. Write scores to Supermemory.")
  5. wait_for_agents([pb-1, gnina-1])
  6. spawn_subagent(task="Search Supermemory for the validated pose,
       run bind-plip profile. Write interaction summary to Supermemory.")
  7. wait_for_agents([plip-1])
  8. memory_search: all findings for this run
     memory_profile: aggregated state
  9. Synthesize consensus, assign confidence, return answer
```

### 7.2 Library Screening

```
User: "Screen these 100 ligands against CDK2, find the top 5"

Orchestrator:
  1. memory_add: plan + ligand manifest
  2. Split ligands into 10 batches
  3. spawn 10 subagents in parallel_group="screen", each:
       "Run bind-boltz predict on ligands {N}-{M}. For each ligand,
        memory_add the binder probability and pose path with
        metadata {tool: boltz, ligand_id: ..., binder_probability: ...}"
  4. wait_for_agents(screen group)
  5. memory_search: filter binder_probability >= 0.7, rank, take top 10
  6. spawn subagent: "Run bind-posebusters on these 10 poses"
     spawn subagent: "Run bind-gnina score on these 10 poses"
  7. wait, then memory_search for plausible + high-scoring subset
  8. spawn subagent: "Run bind-plip on top 5"
  9. Synthesize final ranking with cross-tool evidence

### 7.3 General Research Task (non-tool)

```
User: "What do we know about CDK2 resistance mutations and how
       they affect binding of known inhibitors?"

Orchestrator:
  1. spawn_subagent(role="researcher", task="Search Supermemory for any
       prior CDK2 binding analyses. Also use bind-qmd to find relevant
       skills, specs, or notes in the local repository. Write a research
       summary to Supermemory.")
  2. spawn_subagent(role="researcher", task="Search Supermemory for
       historical screening results involving CDK2 mutants. Compare
       binder probabilities across wild-type and mutant targets.
       Write a comparison table to Supermemory.")
  3. wait_for_agents([research-1, research-2])
  4. memory_search: pull both summaries
  5. Synthesize a narrative answer with citations to specific runs
```

---

## 8. Deployment

### 8.1 Install

```bash
# Install CLI tools
uv pip install -e ".[all]"

# Or individual tool groups
uv pip install -e ".[boltz]"      # includes PyTorch, boltz
uv pip install -e ".[gnina]"      # includes rdkit (for SDF parsing)
uv pip install -e ".[posebusters]" # includes posebusters, rdkit
uv pip install -e ".[plip]"       # includes plip, openbabel

# gnina binary via Docker
docker pull gnina/gnina:latest
```

### 8.2 Environment Variables

| Variable | Purpose | Default |
|----------|---------|---------|
| `BIND_TOOLS_DEVICE` | Default compute device | auto-detect |
| `BIND_TOOLS_WORKSPACE` | Default workspace root | `./workspace` |
| `OPENROUTER_API_KEY` | LLM backend API key | required for agent mode |
| `BIND_TOOLS_MODEL` | Default LLM model | `anthropic/claude-sonnet-4` |
| `SUPERMEMORY_API_KEY` | Supermemory API key | optional (falls back to local Markdown) |
| `DOCKER_HOST` | Docker daemon | system default |

### 8.3 Doctor Command

Every wrapper has `doctor` to verify its environment:

```bash
$ bind-boltz doctor
✓ Python 3.12.8
✓ boltz 1.0.0 installed
✓ PyTorch 2.5.1 (CUDA 12.4 available)
✓ GPU: NVIDIA A100 (cuda:0)
✗ MSA server not reachable (optional)

$ bind-gnina doctor
✓ Docker available (27.4.0)
✓ gnina/gnina:latest image pulled
✓ GPU passthrough: supported (nvidia-container-toolkit)
```

---

## 9. Data Flow Diagram

```
                    ┌──────────────────────┐
                    │   Request (YAML/JSON) │
                    │   or CLI flags        │
                    └──────────┬───────────┘
                               │
                               ▼
                    ┌──────────────────────┐
                    │  Pydantic Validation  │
                    │  (against JSON schema)│
                    └──────────┬───────────┘
                               │
                    ┌──────────┴───────────┐
                    │                      │
              ┌─────▼─────┐         ┌──────▼──────┐
              │ --dry-run  │         │   Execute    │
              │ Print plan │         │  upstream    │
              └────────────┘         └──────┬──────┘
                                            │
                               ┌────────────┼────────────┐
                               │            │            │
                         ┌─────▼────┐ ┌─────▼────┐ ┌────▼─────┐
                         │ Parse    │ │ Collect  │ │ Collect  │
                         │ outputs  │ │ warnings │ │ artifacts│
                         └─────┬────┘ └─────┬────┘ └────┬─────┘
                               │            │            │
                               └────────────┼────────────┘
                                            │
                                            ▼
                               ┌──────────────────────┐
                               │  Result Envelope      │
                               │  (JSON + optional YAML)│
                               └──────────────────────┘
```
