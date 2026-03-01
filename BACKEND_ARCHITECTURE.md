# Backend Architecture

Complete reference for the bind-tools backend: CLI wrappers, agent harness, database tracking, and how data flows between them.

---

## System Overview

```
                          ┌──────────────────────────────────┐
                          │         bind-agent chat          │
                          │       (LLM Agent Loop)           │
                          └────────┬──────────┬──────────────┘
                      spawn_subagent│          │ command tool
                                   │          ▼
                    ┌──────────────┐│  ┌──────────────────────┐
                    │  Subagent    ││  │  CLI Tools (bind-*)   │
                    │  (Thread)    ││  │  resolve, boltz,      │
                    │  same loop   ││  │  gnina, plip, etc.    │
                    └──────┬───────┘│  └──────────┬───────────┘
                           │        │             │
                           │        │     write_result()
                           │        │             │
                           │        │    ┌────────▼──────────┐
                           │        │    │  inject_agent_context
                           │        │    │  _push_to_db()     │
                           │        │    │  _record_viz_artifacts
                           │        │    └────────┬───────────┘
                           │        │             │
                           ▼        ▼             ▼
                    ┌─────────────────────────────────────────┐
                    │              Postgres                    │
                    │  agent_runs · viz_artifacts · hypotheses │
                    │  pipeline_steps · tool_invocations       │
                    └─────────────────────────────────────────┘
```

Key design principle: **the LLM agent never interacts with the database**. All tracking happens transparently inside the CLI tools via `write_result()` and inside the agent loop's start/finish hooks. The agent's context window stays clean.

---

## CLI Tools

All entry points registered in `pyproject.toml`:

| Command | Module | Subcommands |
|---------|--------|-------------|
| `bind-agent` | `bind_tools.agent.cli:main` | `chat`, `doctor` |
| `bind-resolve` | `bind_tools.resolve.cli:app` | `protein`, `ligand`, `binders`, `search`, `doctor`, `schema` |
| `bind-boltz` | `bind_tools.boltz.cli:app` | `predict`, `doctor`, `schema` |
| `bind-gnina` | `bind_tools.gnina.cli:app` | `dock`, `score`, `minimize`, `doctor`, `schema` |
| `bind-posebusters` | `bind_tools.posebusters.cli:app` | `check`, `doctor`, `schema` |
| `bind-plip` | `bind_tools.plip.cli:app` | `profile`, `doctor`, `schema` |
| `bind-qmd` | `bind_tools.qmd.cli:app` | `query`, `doctor`, `schema` |

Every tool accepts three input modes: `--request <yaml/json>`, `--stdin-json`, or direct CLI flags. Every tool emits results via `--json-out` and optionally `--yaml-out`.

---

## Envelope Protocol

All tool inputs and outputs follow the `binding.dev/v1` typed envelope defined in `src/bind_tools/common/envelope.py`.

### Metadata

```python
class Metadata(BaseModel):
    request_id: str   # "req-<hex12>", auto-generated
    created_at: datetime  # UTC
    labels: dict[str, str]
    agent_id: str | None  # injected from BIND_AGENT_ID env var
    run_id: str | None    # injected from BIND_RUN_ID env var
```

### BaseRequest

```python
class BaseRequest(BaseModel):
    api_version: str  # "binding.dev/v1"
    kind: str         # e.g. "GninaDockRequest"
    metadata: Metadata
```

### BaseResult

```python
class BaseResult(BaseModel):
    api_version: str           # "binding.dev/v1"
    kind: str                  # e.g. "GninaResult", "ResolveProteinResult"
    metadata: Metadata
    tool: str                  # "gnina", "resolve", "boltz", etc.
    tool_version: str
    wrapper_version: str       # "0.1.0"
    status: str                # "succeeded" | "failed" | "partial"
    inputs_resolved: dict      # echoed/normalized inputs
    parameters_resolved: dict  # echoed/normalized params
    summary: dict              # key results (varies per tool)
    artifacts: dict            # file paths produced (varies per tool)
    warnings: list[str]
    errors: list[str]
    provenance: dict
    runtime_seconds: float
```

All fields use camelCase aliases for JSON serialization (e.g. `inputsResolved`, `runtimeSeconds`).

### Exit Codes

| Code | Meaning | Error Class |
|------|---------|-------------|
| 0 | Success | — |
| 2 | Validation error | `ValidationError` |
| 3 | Input missing | `InputMissingError` |
| 4 | Upstream failure | `UpstreamError` |
| 5 | Timeout | `TimeoutError` |
| 6 | Partial success | — |
| 7 | Unsupported | `UnsupportedError` |

---

## Common Infrastructure

### `cli_base.py` — The `write_result()` Chokepoint

Every CLI tool calls `write_result(result, json_out, yaml_out)` to emit its output. This single function handles:

1. **`inject_agent_context(result)`** — reads `BIND_AGENT_ID` and `BIND_RUN_ID` from environment, stamps them into `result.metadata.agent_id` and `result.metadata.run_id`.
2. **`_push_to_db(result, json_out)`** — records a `tool_invocations` row and extracts viz artifacts.
3. **`_record_viz_artifacts(result, json_out)`** — inspects `result.kind` to extract specific file paths:

| `result.kind` | Artifacts Extracted | Metadata JSONB |
|---------------|-------------------|----------------|
| `ResolveProteinResult` | `protein_fasta`, `protein_pdb`/`protein_cif` | `{uniprot, gene}`, `{pdb_id}` |
| `ResolveLigandResult` | `ligand_sdf` | `{smiles, molecular_weight}` |
| `BoltzPredictResult` | `complex_cif`, `confidence_json` | `{binder_probability, affinity_value}` |
| `GninaResult` | `docked_sdf` | `{cnn_score, cnn_affinity, energy_kcal_mol, num_poses}` |
| `PlipProfileResult` | `plip_output_dir` | full summary dict |
| *(any)* | `result_json` (the envelope itself) | — |

This means **zero changes to individual CLI tool files** are needed for DB tracking. All recording is centralized.

### `runner.py` — Subprocess and Docker

- **`detect_device()`** — checks `BIND_TOOLS_DEVICE` env, then `torch.cuda.is_available()`, falls back to `"cpu"`.
- **`run_subprocess(cmd, timeout_s, cwd, env)`** — wraps `subprocess.run` with timeout handling.
- **`run_docker(image, cmd, volumes, device, timeout_s)`** — builds `docker run --rm` with volume mappings, `--platform linux/amd64` on ARM, `--gpus all` when not CPU.

---

## Agent Harness

Located in `src/bind_tools/agent/`. The LLM agent orchestrates the full binding analysis pipeline by running CLI tools as shell commands.

### Config (`config.py`)

`AgentConfig` loaded via `AgentConfig.from_env(**overrides)`:

| Field | Default | Env Var |
|-------|---------|---------|
| `api_key` | `""` | `BIND_AGENT_API_KEY` or `OPENROUTER_API_KEY` |
| `base_url` | Modal vLLM endpoint | `BIND_AGENT_BASE_URL` |
| `model` | `openai/gpt-oss-120b` | `BIND_AGENT_MODEL` or `BIND_TOOLS_MODEL` |
| `workspace_root` | `./workspace` | `BIND_TOOLS_WORKSPACE` |
| `run_id` | `run-YYYYMMDD-HHMMSS-<hex6>` | — |
| `agent_id` | `agent-<hex12>` | `BIND_AGENT_ID` |
| `parent_agent_id` | `None` | `BIND_PARENT_AGENT_ID` |
| `db_url` | `None` | `BIND_DB_URL` or `DATABASE_URL` |
| `max_turns` | 30 | — |
| `command_timeout_s` | 600 | — |
| `max_cmd_output_chars` | 1,500 | — |
| `max_read_chars` | 12,000 | — |

### Agent Loop (`loop.py`)

`run_agent(user_message, config, workspace, client) -> AgentRun`

1. Builds system prompt via `build_system_prompt(config, workspace)`.
2. Records agent start in DB (no-op if no DB).
3. Loops up to `max_turns`:
   - Calls `client.chat.completions.create` with `temperature=0.1`, `max_tokens=8192`.
   - **Dual tool-calling mode**: if the API returns native `message.tool_calls`, uses them directly. Otherwise, parses JSON tool calls from the text content (supports 4 formats).
   - Executes each tool call via `executor.execute(name, args_json)`.
   - Feeds results back as `role: "tool"` (native) or `role: "user"` with `[Tool result: name]` prefix (text-based).
4. Records agent finish in DB.
5. Calls `executor.shutdown()` to wait for any subagent threads.

### Tools (`tools.py`)

8 tools available to the LLM:

| Tool | Description |
|------|-------------|
| `command` | Execute shell commands. Available CLIs: `bind-resolve`, `bind-boltz`, `bind-gnina`, `bind-plip`, `bind-posebusters`, `bind-qmd`. Also standard shell commands. |
| `read_file` | Read files up to 12KB. Rejects PDB/CIF/SDF as too large. |
| `list_files` | List directory contents with types and sizes. |
| `write_file` | Write content to a file (auto-creates parents). |
| `think` | No-op scratchpad for planning. |
| `checklist` | Track per-hypothesis pipeline progress (6 steps). |
| `spawn_subagent` | Launch a child agent asynchronously. Returns immediately. |
| `check_subagent` | Poll or block-wait for a subagent's result. |

### Executor (`executor.py`)

`ToolExecutor` dispatches tool calls to handler methods:

- **Commands** run in the workspace directory with `BIND_AGENT_ID`/`BIND_RUN_ID` injected into the subprocess environment and the project `.venv/bin` prepended to `PATH`.
- **Command stdout** is truncated to 1,500 chars — real data flows through `--json-out` files.
- **read_file** hard-rejects files over 12KB (doesn't truncate — refuses entirely).
- **Checklist** is an in-memory dict keyed by hypothesis name, tracking 6 pipeline steps: `resolve_protein`, `resolve_ligand`, `boltz_predict`, `gnina_dock`, `posebusters_check`, `plip_profile`.
- **spawn_subagent** submits `run_agent()` to a `ThreadPoolExecutor(max_workers=4)` and returns immediately.
- **check_subagent** looks up the `Future` by agent_id. With `wait=false` returns `{"status": "running"}` if not done. With `wait=true` blocks until completion.

### Subagent Architecture

Subagents are full independent agent loops running on background threads:

```
Orchestrator Agent (main thread)
  │
  ├─ spawn_subagent("boltz-egfr") ──→ Thread 1: run_agent(child_config)
  │   returns immediately               │ same tools, same workspace
  │                                      │ own agent_id, parent_agent_id set
  │                                      ▼
  ├─ spawn_subagent("gnina-egfr") ──→ Thread 2: run_agent(child_config)
  │   returns immediately               │
  │                                      ▼
  ├─ check_subagent("boltz-egfr", wait=false)
  │   → {"status": "running"}
  │
  ├─ check_subagent("boltz-egfr", wait=true)
  │   → blocks → {"status": "completed", "final_response": "...", "turns": 5}
  │
  ├─ check_subagent("gnina-egfr", wait=true)
  │   → {"status": "completed", "final_response": "...", "turns": 4}
  │
  └─ Synthesizes results into final answer
```

Child agents inherit the parent's `api_key`, `base_url`, `workspace_root`, `run_id`, and `db_url`. They get their own `agent_id` and `parent_agent_id = parent.agent_id`. They have the full toolbox including `spawn_subagent` (recursive spawning is allowed).

### System Prompt (`prompt.py`)

Assembled from 7 sections:

1. Core identity prompt (`binding_agent_spec/prompts/binding-agent-system-prompt.md`)
2. Tool calling protocol (text-based JSON format instructions)
3. Operating rules (`binding_agent_spec/AGENTS.md`)
4. Workspace layout description (directories, CLI flag patterns)
5. Tool skills (7 SKILL.md files inlined)
6. Pipeline instructions (6-step file chaining with exact CLI commands)
7. Subagent usage instructions (when to spawn, how to coordinate)

### Workspace (`workspace.py`)

Each run creates `<workspace_root>/<run_id>/` with 8 subdirectories:

| Directory | Contents | CLI Flag |
|-----------|----------|----------|
| `proteins/` | FASTA, PDB, CIF | `--download-dir proteins/` |
| `ligands/` | SDF files | `--download-dir ligands/` |
| `boltz/` | Boltz-2 outputs | `--artifacts-dir boltz/` |
| `docking/` | gnina outputs | `--artifacts-dir docking/` |
| `validation/` | PoseBusters results | `--artifacts-dir validation/` |
| `interactions/` | PLIP profiles | `--artifacts-dir interactions/` |
| `requests/` | Generated YAML/JSON | `--request requests/my.yaml` |
| `results/` | Result envelopes | `--json-out results/name.json` |

### Run Tracking (`models.py`)

```python
class ToolCall:     # id, name, arguments, result, elapsed_s
class Turn:         # turn_number, assistant_content, tool_calls, finish_reason, timestamp
class AgentRun:     # run_id, agent_id, parent_agent_id, workspace_root, model,
                    # started_at, finished_at, turns, token counts, final_response, status
```

Status values: `running`, `completed`, `max_turns`, `error`.

---

## Database Module

Located in `src/bind_tools/db/`. Entirely optional — all operations gracefully no-op when `BIND_DB_URL` is not set or `psycopg2` is not installed. The DB never blocks tool execution.

### Connection (`connection.py`)

- `get_db_url()` — reads `BIND_DB_URL` or `DATABASE_URL` from env.
- `is_db_available()` — returns `bool`.
- `get_connection()` — context manager yielding a `psycopg2` connection (auto-commit, rollback on exception) or `None`.

### Recorder (`recorder.py`)

`DbRecorder` — stateless class with all static methods. Lazily applies schema on first use (cached via module-level flag). All methods catch exceptions and log rather than propagating.

| Method | Table | When Called |
|--------|-------|-------------|
| `record_agent_start()` | `agent_runs` | Agent loop start |
| `record_agent_finish()` | `agent_runs` | Agent loop end |
| `record_tool_invocation()` | `tool_invocations` | Every `write_result()` call |
| `record_viz_artifact()` | `viz_artifacts` | Every `write_result()` call (per artifact) |
| `record_hypothesis()` | `hypotheses` | On demand |
| `record_pipeline_step()` | `pipeline_steps` | On demand |

---

## Postgres Schema

5 tables, all created idempotently via `CREATE TABLE IF NOT EXISTS`.

### `agent_runs` — Agent Hierarchy

Tracks parent/child agent relationships and run outcomes.

```sql
CREATE TABLE IF NOT EXISTS agent_runs (
    agent_id          TEXT PRIMARY KEY,
    run_id            TEXT NOT NULL,
    parent_agent_id   TEXT REFERENCES agent_runs(agent_id),
    role              TEXT,
    task              TEXT,
    model             TEXT,
    status            TEXT NOT NULL DEFAULT 'pending',
    workspace_root    TEXT,
    started_at        TIMESTAMPTZ DEFAULT NOW(),
    finished_at       TIMESTAMPTZ,
    total_turns       INTEGER DEFAULT 0,
    prompt_tokens     INTEGER DEFAULT 0,
    completion_tokens INTEGER DEFAULT 0,
    total_tokens      INTEGER DEFAULT 0,
    final_response    TEXT,
    created_at        TIMESTAMPTZ DEFAULT NOW()
);
```

Indexes: `run_id`, `parent_agent_id`, `status`.

Example query — get full agent tree for a run:
```sql
SELECT agent_id, parent_agent_id, status, total_turns, total_tokens
FROM agent_runs WHERE run_id = 'run-20260228-...' ORDER BY created_at;
```

### `hypotheses` — Binding Hypotheses

Each protein-ligand pair being investigated.

```sql
CREATE TABLE IF NOT EXISTS hypotheses (
    id              TEXT PRIMARY KEY,
    run_id          TEXT NOT NULL,
    agent_id        TEXT REFERENCES agent_runs(agent_id),
    protein_name    TEXT,
    ligand_name     TEXT,
    status          TEXT NOT NULL DEFAULT 'pending',
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);
```

Indexes: `run_id`, `agent_id`.

### `pipeline_steps` — Per-Hypothesis Step Outcomes

Tracks each of the 6 pipeline steps with confidence scores.

```sql
CREATE TABLE IF NOT EXISTS pipeline_steps (
    id              SERIAL PRIMARY KEY,
    hypothesis_id   TEXT NOT NULL REFERENCES hypotheses(id),
    agent_id        TEXT REFERENCES agent_runs(agent_id),
    step_name       TEXT NOT NULL,
    status          TEXT NOT NULL DEFAULT 'pending',
    result_file     TEXT,
    request_id      TEXT,
    confidence      JSONB,
    note            TEXT,
    started_at      TIMESTAMPTZ,
    finished_at     TIMESTAMPTZ,
    runtime_seconds FLOAT,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);
```

Indexes: `hypothesis_id`, `agent_id`.

The `confidence` JSONB carries tool-specific scores:

| Step | Example `confidence` |
|------|---------------------|
| `boltz_predict` | `{"binder_probability": 0.92, "affinity_value": -7.2}` |
| `gnina_dock` | `{"cnn_score": 0.85, "cnn_affinity": -7.2, "energy_kcal_mol": -9.1}` |
| `posebusters_check` | `{"passed_poses": 1, "failed_poses": 0}` |

### `viz_artifacts` — Visualization File Registry

Every file produced by every tool, tagged with the agent that produced it and confidence metadata where available.

```sql
CREATE TABLE IF NOT EXISTS viz_artifacts (
    id              SERIAL PRIMARY KEY,
    run_id          TEXT NOT NULL,
    agent_id        TEXT,
    request_id      TEXT,
    hypothesis_id   TEXT REFERENCES hypotheses(id),
    tool            TEXT NOT NULL,
    artifact_type   TEXT NOT NULL,
    file_path       TEXT NOT NULL,
    file_format     TEXT,
    label           TEXT,
    metadata        JSONB DEFAULT '{}',
    created_at      TIMESTAMPTZ DEFAULT NOW()
);
```

Indexes: `run_id`, `agent_id`, `tool`, `artifact_type`, `hypothesis_id`.

The `metadata` JSONB carries confidence scores when the tool produces them:

| Tool | `artifact_type` | Example `metadata` |
|------|-----------------|-------------------|
| `resolve` | `protein_fasta` | `{"uniprot": "P00533", "gene": "EGFR"}` |
| `resolve` | `protein_cif` | `{"pdb_id": "1M17"}` |
| `resolve` | `ligand_sdf` | `{"smiles": "c1cc2c(...)...", "molecular_weight": 393.4}` |
| `boltz` | `complex_cif` | `{"binder_probability": 0.92, "affinity_value": -7.2}` |
| `gnina` | `docked_sdf` | `{"cnn_score": 0.85, "cnn_affinity": -7.2, "energy_kcal_mol": -9.1}` |
| `plip` | `plip_output_dir` | full PLIP summary dict |

Example query — get all visualization files for a run:
```sql
SELECT tool, artifact_type, file_path, file_format, metadata
FROM viz_artifacts WHERE run_id = 'run-...' ORDER BY created_at;
```

Example query — get all artifacts from a specific subagent:
```sql
SELECT tool, artifact_type, file_path, metadata
FROM viz_artifacts WHERE agent_id = 'agent-abc123' ORDER BY created_at;
```

Example query — get all artifacts with confidence scores:
```sql
SELECT tool, artifact_type, file_path, metadata
FROM viz_artifacts
WHERE metadata != '{}' AND run_id = 'run-...'
ORDER BY created_at;
```

### `tool_invocations` — CLI Call Log

Every CLI tool invocation with inputs, outputs, and timing.

```sql
CREATE TABLE IF NOT EXISTS tool_invocations (
    id              SERIAL PRIMARY KEY,
    run_id          TEXT NOT NULL,
    agent_id        TEXT,
    request_id      TEXT,
    tool            TEXT NOT NULL,
    subcommand      TEXT,
    status          TEXT NOT NULL,
    runtime_seconds FLOAT,
    inputs          JSONB DEFAULT '{}',
    summary         JSONB DEFAULT '{}',
    errors          JSONB DEFAULT '[]',
    created_at      TIMESTAMPTZ DEFAULT NOW()
);
```

Indexes: `run_id`, `agent_id`.

---

## Data Flow

### Agent Identity Propagation

```
AgentConfig.agent_id
  │
  ├─→ executor._handle_command()
  │     sets env["BIND_AGENT_ID"] and env["BIND_RUN_ID"]
  │       │
  │       ▼
  │     subprocess: bind-resolve protein --name EGFR --json-out results/protein.json
  │       │
  │       ├─→ inject_agent_context(result)
  │       │     reads BIND_AGENT_ID/BIND_RUN_ID from env
  │       │     stamps result.metadata.agent_id / run_id
  │       │
  │       ├─→ _push_to_db(result)
  │       │     INSERT INTO tool_invocations (agent_id=...)
  │       │     INSERT INTO viz_artifacts (agent_id=...)
  │       │
  │       └─→ JSON output file contains agentId/runId in metadata
  │
  ├─→ _db_record_agent_start(config)
  │     INSERT INTO agent_runs (agent_id, parent_agent_id, ...)
  │
  └─→ _db_record_agent_finish(config, run)
        UPDATE agent_runs SET status=..., finished_at=NOW()
```

### Pipeline File Chaining

The agent follows a strict pattern for each pipeline step:

```
1. command: bind-resolve protein --name EGFR --json-out results/protein.json
2. read_file: results/protein.json
   → extract summary.fasta_path, summary.downloaded_path
3. checklist: update resolve_protein → done

4. command: bind-resolve ligand --name erlotinib --json-out results/ligand.json
5. read_file: results/ligand.json
   → extract summary.sdf_path
6. checklist: update resolve_ligand → done

7. command: bind-boltz predict --protein-fasta <fasta> --ligand-sdf <sdf> --json-out results/boltz.json
8. read_file: results/boltz.json
   → extract artifacts.primaryComplexPath
9. checklist: update boltz_predict → done

... and so on for gnina, posebusters, plip
```

Command stdout is truncated (1,500 chars) so the agent is forced to read the JSON result file for actual data.

---

## Infrastructure

### Docker Compose (`docker-compose.yml`)

Single Postgres 16 service:

```yaml
services:
  db:
    image: postgres:16
    ports: ["5432:5432"]
    environment:
      POSTGRES_DB: bindops
      POSTGRES_USER: bind
      POSTGRES_PASSWORD: bind
    volumes:
      - pgdata:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U bind -d bindops"]
      interval: 2s
      timeout: 5s
      retries: 10
```

### Run Script (`run.sh`)

One command to start everything:

```bash
./run.sh "Analyze binding of erlotinib to EGFR"
```

Steps: starts Postgres via `docker compose up -d --wait`, exports `BIND_DB_URL`, installs `psycopg2-binary` if needed, runs `bind-agent chat "$@"`.

### Dependencies (`pyproject.toml`)

```
Core:     httpx, openai, pydantic, rcsbsearchapi, typer, pyyaml, rich
Optional: psycopg2-binary (extra: "db")
Dev:      pytest, pytest-asyncio, ruff, psycopg2-binary
```

Python: `>=3.11,<3.13`. Build: setuptools.

---

## Tool Modules Reference

### Resolve (`bind_tools.resolve`)

Resolves protein and ligand identifiers to downloadable structure files.

**Protein resolution** (`resolve_protein`):
UniProt search (5-strategy cascade: direct accession, exact gene, protein name, gene, full-text) → FASTA download → PDB structure search via `rcsbsearchapi` → fetch details and binding sites from RCSB REST/GraphQL → rank structures (ligand-bound X-ray with best resolution first) → download best as PDB + CIF.

**Ligand resolution** (`resolve_ligand`):
Detects query type (PubChem CID, SMILES, CCD code, or compound name) → PubChem PUG-REST lookup → download 2D/3D SDF → optional RDKit 3D fallback if PubChem has no conformer.

**Binders** (`resolve_binders`):
Protein → UniProt accession → ChEMBL target ID → bioactivity data (filtered by pChEMBL) + approved drugs via mechanism-of-action endpoint.

### Boltz (`bind_tools.boltz`)

Wraps Boltz-2 structure prediction. Translates `BoltzPredictSpec` to Boltz v2 upstream YAML format, runs `boltz predict` as a subprocess. Parses confidence JSON (`ptm`, `iptm`, `complex_plddt`, `ranking_score`) and affinity JSON (`binder_probability`, `affinity_value`).

### Gnina (`bind_tools.gnina`)

Wraps gnina molecular docking via Docker (`gnina/gnina:latest`). Three modes: `dock` (full docking), `score` (rescore poses), `minimize` (local optimization). Builds volume mappings with deduplication, translates host paths to container paths. Parses output SDF via RDKit `SDMolSupplier` for `CNNscore`, `CNNaffinity`, `minimizedAffinity`.

### PoseBusters (`bind_tools.posebusters`)

Validates predicted poses against chemical/physical plausibility checks. Three configs: `"redock"` (protein + reference), `"dock"` (protein only), `"mol"` (standalone). Categorizes failures: fatal (sanitization, all_atoms_connected), major (bond_lengths, bond_angles, steric_clash, volume_overlap), minor (everything else).

### PLIP (`bind_tools.plip`)

Profiles protein-ligand interactions. Loads PDB, calls `PDBComplex.analyze()`, extracts 11 interaction types (hydrogen bonds, hydrophobic contacts, pi-stacking, pi-cation, salt bridges, water bridges, halogen bonds, metal complexes). Aggregates counts and interacting residue labels.

### QMD (`bind_tools.qmd`)

Local file retrieval engine for the agent. Searches `binding_agent_spec/` for skills, specs, schemas, examples, and documentation. Scores files by term frequency in filename (+10) and content (+count). Returns top-k results with snippets.

---

## Environment Variables

| Variable | Used By | Purpose |
|----------|---------|---------|
| `BIND_AGENT_API_KEY` | Agent | LLM API key (preferred) |
| `OPENROUTER_API_KEY` | Agent | LLM API key (fallback) |
| `BIND_AGENT_BASE_URL` | Agent | LLM endpoint URL |
| `BIND_AGENT_MODEL` | Agent | Model identifier (preferred) |
| `BIND_TOOLS_MODEL` | Agent | Model identifier (fallback) |
| `BIND_TOOLS_WORKSPACE` | Agent | Workspace root directory |
| `BIND_AGENT_ID` | Agent, CLI tools | Agent identity (propagated to subprocesses) |
| `BIND_RUN_ID` | CLI tools | Run identity (propagated to subprocesses) |
| `BIND_PARENT_AGENT_ID` | Agent | Parent agent for hierarchy |
| `BIND_DB_URL` | DB module | Postgres connection string (preferred) |
| `DATABASE_URL` | DB module | Postgres connection string (fallback) |
| `BIND_TOOLS_DEVICE` | Runner | Force compute device (`cuda:0`, `cpu`) |

---

## File Structure

```
src/bind_tools/
├── common/
│   ├── envelope.py      # BaseRequest, BaseResult, Metadata
│   ├── errors.py        # Exit codes, error hierarchy
│   ├── runner.py         # Subprocess, Docker, device detection
│   └── cli_base.py       # load_request, write_result, inject_agent_context, _push_to_db
├── agent/
│   ├── cli.py            # bind-agent chat/doctor commands
│   ├── config.py         # AgentConfig (env + CLI flags)
│   ├── client.py         # OpenAI SDK client factory
│   ├── loop.py           # run_agent() — core agentic loop
│   ├── executor.py       # ToolExecutor — dispatches tool calls
│   ├── tools.py          # 8 tool definitions (JSON Schema)
│   ├── prompt.py         # System prompt assembly (7 sections)
│   ├── models.py         # AgentRun, Turn, ToolCall
│   └── workspace.py      # Workspace directory management
├── db/
│   ├── __init__.py       # Exports: get_connection, is_db_available, DbRecorder
│   ├── connection.py     # get_db_url(), get_connection() context manager
│   ├── schema.py         # CREATE TABLE IF NOT EXISTS (5 tables)
│   └── recorder.py       # DbRecorder static methods
├── resolve/              # Protein/ligand/binders resolution
├── boltz/                # Boltz-2 structure prediction wrapper
├── gnina/                # gnina Docker docking wrapper
├── posebusters/          # PoseBusters validation wrapper
├── plip/                 # PLIP interaction profiling wrapper
├── qmd/                  # Local file retrieval engine
├── protein/              # UniProt, RCSB PDB search/download
└── ligand/               # PubChem search/download, RDKit 3D gen

docker-compose.yml        # Postgres 16 for local dev
run.sh                    # One-command startup
binding_agent_spec/       # Read-only specs, skills, schemas, prompts
```
