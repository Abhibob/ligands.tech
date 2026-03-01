# BindingOps — Complete Technology Stack

> Comprehensive reference for every technology, library, model, format, and service used in the project.

---

## Table of Contents

1. [Core Platform](#1-core-platform)
2. [Python Dependencies](#2-python-dependencies)
3. [CLI Tools](#3-cli-tools)
4. [Agent Architecture](#4-agent-architecture)
5. [LLM / AI Models](#5-llm--ai-models)
6. [ML Models & Scoring Functions](#6-ml-models--scoring-functions)
7. [Database](#7-database)
8. [API Server (Backend)](#8-api-server-backend)
9. [Frontend](#9-frontend)
10. [Cloud GPU / Modal](#10-cloud-gpu--modal)
11. [Docker](#11-docker)
12. [External APIs](#12-external-apis)
13. [File Formats](#13-file-formats)
14. [Tool ↔ Format Matrix](#14-tool--format-matrix)
15. [End-to-End Pipeline Data Flow](#15-end-to-end-pipeline-data-flow)
16. [Environment Variables](#16-environment-variables)
17. [Deployment](#17-deployment)

---

## 1. Core Platform

| Component | Technology | Version / Notes |
|-----------|-----------|----------------|
| Language | Python | >=3.9, <3.13 |
| Package manager | uv | `~/.local/bin/uv` |
| Build system | setuptools | >=68.0 (`setuptools.build_meta`) |
| Source layout | `src/bind_tools/` | PEP 517 compliant |
| Linter | Ruff | >=0.3.0 (line-length 100, target py39, rules E/F/I/N/UP/B/A) |
| Test runner | pytest | >=8.0.0 with `pytest-asyncio>=0.23.0` (asyncio_mode=auto) |
| Device detection | Custom | `BIND_TOOLS_DEVICE` env → `torch.cuda.is_available()` → `"cpu"` |

---

## 2. Python Dependencies

### Core (always installed)

| Package | Version | Purpose |
|---------|---------|---------|
| httpx | >=0.27.0 | HTTP client for external API calls (ChEMBL, PubChem, RCSB, Modal REST) |
| openai | >=1.0.0 | OpenAI-compatible chat completions SDK (used via OpenRouter / Modal) |
| pydantic | >=2.0.0 | Data models with camelCase aliases, validation |
| rcsbsearchapi | >=2.0.0 | RCSB PDB structure search |
| typer | >=0.9.0 | CLI framework for all tools |
| pyyaml | >=6.0 | YAML request/response serialization |
| rich | >=13.0 | Console formatting (tables, colors, spinners) |

### Optional Dependency Groups

| Group | Packages | Purpose |
|-------|----------|---------|
| `api` | `fastapi>=0.110.0`, `uvicorn[standard]>=0.29.0`, `psycopg2-binary>=2.9.0` | FastAPI web server + PostgreSQL |
| `db` | `psycopg2-binary>=2.9.0` | Database recording only |
| `modal` | `modal>=0.73.0`, `python-dotenv>=1.0.0` | Remote GPU execution on Modal |
| `protprep` | `pdbfixer>=1.9`, `openmm>=8.0`, `pdb2pqr>=3.6.0` | Protein structure preparation |
| `batch` | `rdkit>=2023.0` | Batch processing with RDKit |
| `ligprep` | `rdkit>=2023.0`, `meeko>=0.5.0` | Ligand preparation + PDBQT conversion |
| `dev` | `pytest>=8.0.0`, `pytest-asyncio>=0.23.0`, `ruff>=0.3.0`, `psycopg2-binary>=2.9.0` | Development/testing |

### Implicit / Runtime Dependencies

| Package | Required By | Purpose |
|---------|-------------|---------|
| torch | common/runner.py | CUDA detection (`torch.cuda.is_available()`) |
| plip | bind-plip | Protein-ligand interaction profiling |
| posebusters | bind-posebusters | Pose validation |
| rdkit / rdkit-pypi | bind-gnina (SDF parsing), ligprep, binders | SDF parsing, 3D conformer generation |
| Open Babel (`obabel`) | bind-plip, ligprep | Format conversion (MOL2, PDBQT) |
| numpy | protprep | Water distance filtering |
| pandas | posebusters | Tabular results |
| FlagEmbedding | Modal reranker | `BAAI/bge-reranker-v2-m3` model |
| transformers | Modal reranker | Model loading |

---

## 3. CLI Tools

13 registered entry points:

| Entry Point | Module | Description |
|-------------|--------|-------------|
| `bind-api` | `bind_tools.api:main` | FastAPI web server |
| `bind-agent` | `bind_tools.agent.cli:main` | Agent harness / orchestrator |
| `bind-boltz` | `bind_tools.boltz.cli:app` | Boltz-2 structure prediction |
| `bind-gnina` | `bind_tools.gnina.cli:app` | GNINA molecular docking (via Docker) |
| `bind-plip` | `bind_tools.plip.cli:app` | PLIP interaction profiling |
| `bind-posebusters` | `bind_tools.posebusters.cli:app` | PoseBusters pose validation |
| `bind-resolve` | `bind_tools.resolve.cli:app` | Unified protein/ligand/binder resolution |
| `bind-protein` | `bind_tools.protein.cli:main` | Protein resolution |
| `bind-ligand` | `bind_tools.ligand.cli:main` | Ligand resolution |
| `bind-ligprep` | `bind_tools.ligprep.cli:main` | Ligand preparation pipeline |
| `bind-protprep` | `bind_tools.protprep.cli:main` | Protein structure preparation |
| `bind-qmd` | `bind_tools.qmd.cli:app` | Local filesystem document search |
| `bind-search` | `bind_tools.search.cli:main` | Web search |

### Shared Infrastructure (`src/bind_tools/common/`)

| Module | Purpose |
|--------|---------|
| `envelope.py` | Envelope protocol — `apiVersion: binding.dev/v1`, concrete `kind`, `metadata.requestId`, `metadata.createdAt` |
| `errors.py` | Error hierarchy with exit codes: 0=success, 2=validation, 3=input_missing, 4=upstream, 5=timeout, 6=partial, 7=unsupported |
| `runner.py` | `detect_device()`, `run_subprocess()` with timeout, `run_docker()` with GPU passthrough and ARM cross-platform support |
| `cli_base.py` | `load_request()` (YAML/JSON/stdin/flags), `write_result()` (JSON/YAML/stdout + DB recording) |
| `batch.py` | `glob_input_dir()` for batch file discovery |
| `manifest.py` | `write_manifest()` for Markdown batch summaries |

---

## 4. Agent Architecture

### Overview

The agent system (`src/bind_tools/agent/`) implements an autonomous LLM-driven orchestrator that calls CLI tools to execute protein-ligand binding workflows.

### Components

| File | Role |
|------|------|
| `config.py` | `AgentConfig` — LLM endpoint, model, workspace paths, limits (max 500 turns, 600s timeout, 12KB read limit) |
| `client.py` | OpenAI SDK client factory (compatible with OpenRouter / any OpenAI-compatible endpoint) |
| `models.py` | `ToolCall`, `Turn`, `AgentRun` Pydantic models for run tracking |
| `workspace.py` | Per-run directory tree: `proteins/`, `ligands/`, `boltz/`, `docking/`, `validation/`, `interactions/`, `requests/`, `results/` |
| `prompt.py` | System prompt assembly from 8 sections (identity, tool protocol, rules, workspace, skills, pipeline, batch, subagents) |
| `tools.py` | 8 tools in OpenAI function-calling schema format |
| `executor.py` | Tool execution engine with subprocess, filesystem, and subagent management |
| `loop.py` | Core agent loop — supports native OpenAI `tool_calls` and text-based JSON fallback for vLLM endpoints |
| `cli.py` | `bind-agent chat` Typer CLI |

### Agent Tools

| Tool | Purpose |
|------|---------|
| `command` | Execute shell commands (bind-* CLIs, standard Unix) |
| `read_file` | Read files up to 12KB (JSON result envelopes) |
| `list_files` | List directory contents with types/sizes |
| `write_file` | Create files (YAML requests, etc.) |
| `think` | Planning scratchpad (no side effects) |
| `checklist` | Track 6-step pipeline progress per hypothesis |
| `spawn_subagent` | Launch async child agent in background thread (max 4 concurrent) |
| `check_subagent` | Poll or wait for spawned subagent results |

### Subagent Model

- Parent spawns child agents via `ThreadPoolExecutor(max_workers=4)`
- Children inherit config (API key, base URL, workspace, run_id, DB URL)
- Parent-child hierarchy tracked in PostgreSQL `agent_runs` table
- Coordination via shared workspace filesystem and `--json-out` result files

### Event System

Events published to `AgentEventBus` for WebSocket streaming:
`agent_start`, `turn_start`, `tool_call`, `tool_result`, `thinking`, `nudge`, `assistant_text`, `done`

### Spec & Skills (`binding_agent_spec/`)

| Directory | Contents |
|-----------|----------|
| `prompts/` | System prompt (`binding-agent-system-prompt.md`) |
| `AGENTS.md` | 10 core operating rules (evidence policy, confidence levels, workflow) |
| `skills/` | 7 skill files: binding-orchestrator, resolve, boltz2, gnina, posebusters, plip, qmd-search |
| `schemas/` | 13 JSON Schema files for request/result validation |
| `specs/` | 5 wrapper specification documents |
| `examples/` | Sample YAML request files |

---

## 5. LLM / AI Models

### Agent LLM (default)

| Property | Value |
|----------|-------|
| Model | `openai/gpt-oss-120b` |
| Endpoint | `https://benwu408--gpt-oss-120b-serve.modal.run/v1` |
| Protocol | OpenAI Chat Completions API (via OpenAI Python SDK) |
| Temperature | 0.1 |
| Max tokens | 8,192 |
| API key priority | `BIND_AGENT_API_KEY` > `OPENROUTER_API_KEY` |

### Recommended Models (from ARCHITECTURE.md)

| Agent Role | Model | Rationale |
|-----------|-------|-----------|
| Orchestrator | `anthropic/claude-sonnet-4` | Strong reasoning, tool use, planning |
| Tool Subagent | `anthropic/claude-haiku-4-5` | Fast, cheap, structured tool calls |
| Discovery (batch) | `anthropic/claude-haiku-4-5` | High throughput for parallel screening |
| Consensus Synthesis | `anthropic/claude-sonnet-4` | Nuanced scientific interpretation |
| Fallback | `google/gemini-2.5-flash` | Cost-effective fallback |

### Search Reranker

| Property | Value |
|----------|-------|
| Model | `BAAI/bge-reranker-v2-m3` |
| Type | Cross-encoder (~1.1GB) |
| Framework | FlagEmbedding + torch + transformers |
| Runs on | Modal (CPU) |

---

## 6. ML Models & Scoring Functions

### Boltz-2 (Structure Prediction + Affinity)

| Property | Detail |
|----------|--------|
| Tool | `bind-boltz predict` |
| Upstream | `boltz predict` subprocess CLI |
| Type | Protein-ligand co-folding with diffusion + affinity head |
| Input | Protein sequence (FASTA) + ligand (SMILES/SDF/MOL2) |
| Output | Complex structure (PDB/CIF), confidence metrics, affinity prediction |
| GPU | A100 on Modal, or local CUDA |
| Task modes | `structure`, `affinity`, `both` |
| Key params | `recycling_steps`, `diffusion_samples`, `seed`, `use_msa_server` |

**Boltz-2 scoring metrics:**

| Metric | Source | Meaning |
|--------|--------|---------|
| `confidence` | confidence JSON | Overall prediction confidence |
| `ptm` | confidence JSON | Predicted TM-score |
| `iptm` | confidence JSON | Interface pTM (protein-ligand interface quality) |
| `complex_plddt` | confidence JSON | Predicted per-residue LDDT |
| `complex_iplddt` | confidence JSON | Interface pLDDT |
| `ranking_score` | confidence JSON | Combined ranking metric |
| `binder_probability` | affinity JSON | Probability of being a true binder (screening) |
| `affinity_value` | affinity JSON | Predicted binding affinity (ranking) |

### gnina (CNN-Based Docking)

| Property | Detail |
|----------|--------|
| Tool | `bind-gnina dock/score/minimize` |
| Upstream | `gnina` binary via Docker (`gnina/gnina:latest`) |
| Type | AutoDock Vina + CNN pose scoring + CNN affinity prediction |
| GPU | T4 on Modal, or local Docker with `--gpus all` |

**gnina classical scoring functions:**

| Function | Flag | Metric |
|----------|------|--------|
| Vina | `--scoring vina` (default) | Energy kcal/mol (more negative = better) |
| Vinardo | `--scoring vinardo` | Energy kcal/mol |
| AD4 | `--scoring ad4_scoring` | Energy kcal/mol |

**gnina CNN scoring modes:**

| Mode | Flag | Behavior |
|------|------|----------|
| none | `--cnn-scoring none` | No CNN scoring |
| rescore | `--cnn-scoring rescore` (default) | CNN scores final Vina poses |
| refinement | `--cnn-scoring refinement` | Refine poses using CNN gradients |
| all | `--cnn-scoring all` | Full CNN throughout docking |

**gnina per-pose metrics (SDF properties):**

| Property | Type | Meaning |
|----------|------|---------|
| `minimizedAffinity` | float | Vina energy (kcal/mol) |
| `CNNscore` | float 0-1 | Probability pose is correct |
| `CNNaffinity` | float | Predicted pK binding affinity |
| `CNN_VS` | float | CNNscore × CNNaffinity (composite) |

### PoseBusters (Pose Validation)

| Property | Detail |
|----------|--------|
| Tool | `bind-posebusters check` |
| Upstream | PoseBusters Python library |
| Type | Rule-based geometric/chemical validation |
| Dependencies | posebusters, rdkit, pandas |

**Validation configs:** `auto` (default), `mol` (molecule-only), `dock` (pose + protein), `redock` (pose + protein + reference)

**Failure severity:**

| Category | Checks |
|----------|--------|
| Fatal | `sanitization`, `all_atoms_connected` |
| Major | `bond_lengths`, `bond_angles`, `internal_steric_clash`, `volume_overlap_with_protein` |
| Minor | All other checks |

### PLIP (Interaction Profiling)

| Property | Detail |
|----------|--------|
| Tool | `bind-plip profile` |
| Upstream | PLIP Python library (`plip.structure.preparation.PDBComplex`) |
| Dependencies | PLIP, Open Babel |

**11 interaction types detected:**

| Type | Description |
|------|-------------|
| `hbonds_pdon` | Hydrogen bonds (protein donor) |
| `hbonds_ldon` | Hydrogen bonds (ligand donor) |
| `hydrophobic_contacts` | Hydrophobic contacts |
| `pistacking` | Pi-stacking |
| `pication_laro` | Pi-cation (ligand aromatic) |
| `pication_paro` | Pi-cation (protein aromatic) |
| `saltbridge_lneg` | Salt bridges (ligand negative) |
| `saltbridge_pneg` | Salt bridges (protein negative) |
| `waterbridge` | Water bridges |
| `halogen_bonds` | Halogen bonds |
| `metal_complexes` | Metal complexes |

### Protein Preparation (protprep)

| Property | Detail |
|----------|--------|
| Tool | `bind-protprep` |
| Libraries | PDBFixer, pdb2pqr/PROPKA, OpenMM |
| Force field | `amber14-all.xml` (default) |
| Water model | implicit (default) |

**Pipeline steps (in order):**
1. Select chains
2. Replace non-standard residues
3. Fill missing residues/loops
4. Fill missing atoms
5. Remove heterogens
6. Remove water / filter by distance
7. Add hydrogens (pH-aware, default 7.4)
8. Assign protonation states (via pdb2pqr/PROPKA)
9. Energy minimization (via OpenMM — Langevin, 300K, HBonds constraints)

### Ligand Preparation (ligprep)

| Property | Detail |
|----------|--------|
| Tool | `bind-ligprep` |
| Engines | `auto` (rdkit > obabel), `rdkit`, `obabel`, `meeko` |
| 3D generation | RDKit ETKDGv3 + MMFF/UFF optimization |
| Charge model | Gasteiger (default) |

**Pipeline steps:**
1. Resolve input (SDF, MOL2, SMILES, name, CID)
2. Add hydrogens
3. Assign partial charges
4. Generate 3D conformers
5. Write output (SDF, PDBQT, MOL2)

---

## 7. Database

| Property | Value |
|----------|-------|
| Engine | PostgreSQL 16 |
| Driver | `psycopg2-binary` |
| Connection | `BIND_DB_URL` or `DATABASE_URL` env var |
| Default URL | `postgresql://bind:bind@localhost:5432/bindops` |
| Graceful degradation | All DB operations are no-ops when no DB is configured |

### Schema (5 tables, all `CREATE TABLE IF NOT EXISTS`)

**`agent_runs`** (PK: `agent_id TEXT`)
- `run_id`, `parent_agent_id` (self-referential FK), `role`, `task`, `model`, `status`
- `workspace_root`, `started_at`, `finished_at`
- `total_turns`, `prompt_tokens`, `completion_tokens`, `total_tokens`, `final_response`
- Indexes on: `run_id`, `parent_agent_id`, `status`

**`hypotheses`** (PK: `id TEXT`)
- `run_id`, `agent_id` (FK → agent_runs)
- `protein_name`, `ligand_name`, `status`
- `created_at`, `updated_at`

**`pipeline_steps`** (PK: `id SERIAL`)
- `hypothesis_id` (FK → hypotheses), `agent_id` (FK → agent_runs)
- `step_name`, `status`, `result_file`, `request_id`
- `confidence` (JSONB), `note`, `started_at`, `finished_at`, `runtime_seconds`

**`viz_artifacts`** (PK: `id SERIAL`)
- `run_id`, `agent_id`, `request_id`, `hypothesis_id` (FK → hypotheses)
- `tool`, `artifact_type`, `file_path`, `file_format`, `label`, `metadata` (JSONB)

**`tool_invocations`** (PK: `id SERIAL`)
- `run_id`, `agent_id`, `request_id`, `tool`, `subcommand`
- `status`, `runtime_seconds`, `inputs` (JSONB), `summary` (JSONB), `errors` (JSONB)

### Recorder (`DbRecorder`)

Stateless class with static methods. All methods catch and log exceptions — the DB never blocks tool execution. Methods: `ensure_schema()`, `record_agent_start()`, `record_agent_finish()`, `record_tool_invocation()`, `record_viz_artifact()`, `record_hypothesis()`, `record_pipeline_step()`.

---

## 8. API Server (Backend)

| Property | Value |
|----------|-------|
| Framework | FastAPI |
| ASGI server | Uvicorn (`uvicorn[standard]`) |
| Port | 8000 |
| CORS origins | `CORS_ORIGINS` env (default: `http://localhost:5173,http://localhost:3000`) |
| Auto-docs | Swagger UI at `/docs` |

### REST Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/agents` | List top-level agents (filterable by status), includes `child_count` |
| GET | `/api/agents/{agent_id}` | Single agent with `child_count` |
| GET | `/api/agents/{agent_id}/children` | Child agents |
| GET | `/api/agents/{agent_id}/hypotheses` | Hypotheses with nested pipeline_steps |
| GET | `/api/agents/{agent_id}/artifacts` | Visualization artifacts |
| GET | `/api/agents/{agent_id}/invocations` | Tool invocations |
| GET | `/api/hypotheses/{hypothesis_id}` | Single hypothesis with steps |
| GET | `/api/stats` | Aggregate stats (agent_count, hypothesis_count, protein_count, ligand_count) |
| POST | `/api/runs` | Create run — spawns agent in daemon thread, returns `run_id` + `agent_id` |
| GET | `/api/runs/{run_id}` | Poll run status |
| GET | `/api/artifacts/{path}` | Serve workspace files (PDB, SDF, CIF, JSON, YAML, PNG, SVG) with path-traversal protection |

### WebSocket Endpoint

| Path | Description |
|------|-------------|
| `/api/agents/{agent_id}/ws` | Stream live agent events. Sends buffered history on connect, then real-time events. Keepalive pings every 30s. Closes after `done` event. |

### Event Bus (`AgentEventBus`)

Singleton, thread-safe (agent threads publish, async WebSocket handlers subscribe). Uses `asyncio.Queue` per subscriber. Ring buffer of 500 events per agent for late joiners.

### Response Models

All use Pydantic v2 with camelCase aliases: `AgentRunResponse`, `HypothesisResponse`, `PipelineStepResponse`, `VizArtifactResponse`, `ToolInvocationResponse`, `RunCreateRequest`, `RunCreateResponse`, `RunStatusResponse`, `StatsResponse`.

### Chemical MIME Types

| Extension | MIME Type |
|-----------|-----------|
| `.pdb` | `chemical/x-pdb` |
| `.cif` | `chemical/x-cif` |
| `.sdf` | `chemical/x-mdl-sdfile` |

---

## 9. Frontend

Located in `frontend_SAMPLE/`. Project name: `ligands-tech`.

### Core Stack

| Technology | Version | Purpose |
|-----------|---------|---------|
| React | ^19.2.4 | UI framework (StrictMode enabled) |
| React DOM | ^19.2.4 | DOM rendering via `createRoot` |
| TypeScript | ^5.9.3 | Strict mode, ES2020 target, bundler module resolution |
| Vite | ^7.3.1 | Build tool + dev server, ESM modules |
| `@vitejs/plugin-react` | ^5.1.4 | React Fast Refresh + JSX transform |

### Styling

| Technology | Version | Details |
|-----------|---------|---------|
| Tailwind CSS | ^4.2.1 | v4, integrated via `@tailwindcss/vite` plugin |

- **No component library** — all UI is hand-built with Tailwind utility classes
- Custom theme tokens: teal brand colors, score tiers (green/amber/red)
- Custom animations: `shimmer`, `pulse-subtle`, `count-up`
- Custom utilities: `.bg-dot-pattern`, `.text-gradient-shimmer`

**Fonts (Google Fonts):**

| Font | Role |
|------|------|
| DM Serif Display | Headings (serif) |
| Inter (300–700) | Body text (sans-serif) |
| JetBrains Mono | Code / IDs (monospace) |

### Routing

| Technology | Version |
|-----------|---------|
| React Router DOM | ^7.13.1 |

| Route | Page | Description |
|-------|------|-------------|
| `/` | `HomePage` | Landing page with 3D protein scene, stats, prompt input |
| `/agents/:id?` | `AgentsPage` | Running agents + hypothesis cards + live thinking sidebar |
| `/finished/:id?` | `FinishedAgentsPage` | Completed/failed agents with replay |
| `/hypothesis/:hypothesisId` | `HypothesisPage` | 3D binding visualization, score ring, pipeline steps |
| `/results` | `ResultsPage` | Ranked table of all hypotheses |

### Animation

| Technology | Version |
|-----------|---------|
| Framer Motion | ^12.34.3 |

Used for page transitions (`AnimatePresence`), layout animations (`layoutId`), staggered grid entry, hover effects (`whileHover`), scroll-triggered reveals (`whileInView`), sidebar slide-in, table row animations, floating decorative elements.

### 3D Molecular Visualization

| Technology | Version | Purpose |
|-----------|---------|---------|
| Three.js | ^0.183.2 | Core 3D rendering engine |
| @react-three/fiber | ^9.5.0 | React renderer for Three.js |
| @react-three/drei | ^10.7.7 | Helpers (Float, OrbitControls, Html labels) |
| @types/three | ^0.183.1 | TypeScript definitions |

**Custom-built procedural visualization** (no Mol\* or NGL viewer):

| Component | File | Purpose |
|-----------|------|---------|
| `Atom` | `components/three/primitives.tsx` | Sphere geometry with configurable material |
| `Bond` | `components/three/primitives.tsx` | Cylinder connecting two 3D points |
| `BindingModel` | `components/three/BindingModel.tsx` | Procedural protein-ligand binding model — separation distance inversely proportional to binding score, cross-bonds colored by score tier |
| `MiniBindingScene` | `components/three/MiniBindingScene.tsx` | Lightweight version for hypothesis cards |
| `DetailBindingScene` | `components/three/DetailBindingScene.tsx` | Full version with OrbitControls, Float, Html labels |
| `ProteinScene` | `components/home/ProteinScene.tsx` | Hero page alpha helix backbone (24 atoms, helical arrangement) |

### Icons

| Technology | Version |
|-----------|---------|
| Lucide React | ^0.575.0 |

### State Management

**No external state library** — React `useState`, `useEffect`, `useCallback`, `useMemo`, `useRef` only.

- No Redux, Zustand, Jotai, Recoil, or React Query
- Polling with `setInterval` for live updates (3–4 second intervals)
- WebSocket for real-time agent thinking events

### API Communication

| Mechanism | Technology | Details |
|-----------|-----------|---------|
| HTTP | Native `fetch` | Simple `get<T>` / `post<T>` generic helpers |
| WebSocket | Native `WebSocket` | Custom `useAgentEvents(agentId)` hook with auto-reconnect |
| Base URL | `VITE_API_URL` env | Falls back to empty string (uses Vite proxy in dev) |
| Dev proxy | Vite config | `/api` → `http://localhost:8000` (including WebSocket) |

### Score Derivation (`utils/scores.ts`)

Composite score 0–100 from pipeline steps:
- **Boltz `binder_probability`**: 40% weight
- **gnina `cnn_score`**: 40% weight
- **PoseBusters `pass_rate`**: 20% weight

Weights adjust dynamically when data is missing.

### Frontend Directory Structure

```
frontend_SAMPLE/
├── index.html                    # Entry HTML, Google Fonts
├── package.json                  # Dependencies
├── vite.config.ts                # Vite + React + Tailwind + API proxy
├── tsconfig.json                 # Strict TypeScript config
└── src/
    ├── main.tsx                  # React root mount
    ├── App.tsx                   # BrowserRouter + animated routes
    ├── index.css                 # Tailwind v4 + custom theme
    ├── api/
    │   └── client.ts             # REST + artifact URL helpers
    ├── hooks/
    │   └── useAgentEvents.ts     # WebSocket hook for live agent events
    ├── types/
    │   └── index.ts              # All TypeScript interfaces
    ├── utils/
    │   └── scores.ts             # Score derivation from pipeline steps
    ├── pages/
    │   ├── HomePage.tsx
    │   ├── AgentsPage.tsx
    │   ├── FinishedAgentsPage.tsx
    │   ├── HypothesisPage.tsx
    │   └── ResultsPage.tsx
    └── components/
        ├── layout/               # Navbar, PageLayout (Outlet wrapper)
        ├── agents/               # AgentSidebar, HypothesisCard, ThinkingSidebar
        ├── interaction/          # AnalysisPanel, ResidueList
        ├── results/              # ResultsTable, ResultsRow
        ├── shared/               # ScoreBadge, ScoreRing (SVG circular progress)
        ├── three/                # 3D primitives, BindingModel, scenes
        └── home/                 # ProteinScene (hero 3D)
```

---

## 10. Cloud GPU / Modal

**Modal App:** `bind-tools-gpu`

### Container Images

| Image | Base | Python | Key Packages |
|-------|------|--------|-------------|
| `boltz_image` | `debian_slim` | 3.11 | `boltz`, `pyyaml` |
| `gnina_image` | `gnina/gnina:latest` (Docker Hub) | 3.11 (injected) | `rdkit-pypi` |
| `reranker_image` | `debian_slim` | 3.11 | `FlagEmbedding>=1.2.0`, `torch>=2.0.0`, `transformers>=4.33.0,<4.46.0`, `httpx` |

### GPU Classes

| Class | GPU | Timeout | Purpose |
|-------|-----|---------|---------|
| `BoltzPredictor` | **A100** | 30 min | Boltz-2 structure prediction |
| `GninaRunner` | **T4** | 10 min | GNINA docking/scoring/minimization |
| `SearchReranker` | CPU | 2 min | BGE reranker for search results |
| `WebAPI` | CPU | — | FastAPI gateway dispatching to GPU classes |

### Persistent Storage

`bind-tools-boltz-weights` volume mounted at `/root/.boltz` (~3.6 GB Boltz-2 model weights)

### Remote REST API (Modal-hosted)

**Base URL:** `https://benwu408--bind-tools-gpu-webapi-serve.modal.run`
**Auth:** Bearer token via `BIND_TOOLS_API_KEY`
**File transport:** Base64-encoded in JSON (`FileB64` model)
**CORS:** Fully open (`allow_origins=["*"]`)

| Method | Endpoint |
|--------|----------|
| GET | `/v1/health` |
| POST | `/v1/boltz/predict` |
| POST | `/v1/gnina/dock` |
| POST | `/v1/gnina/score` |
| POST | `/v1/gnina/minimize` |
| POST | `/v1/search/rerank` |

### Three Execution Modes (boltz & gnina)

| Mode | Trigger | How It Runs |
|------|---------|-------------|
| **Local** | Default | Subprocess / Docker on local machine |
| **Modal** | `--modal` flag or `BIND_TOOLS_USE_MODAL=1` | Direct Modal SDK call to GPU class |
| **Remote REST** | `REMOTE=on` env var | HTTP POST to Modal-hosted WebAPI |

---

## 11. Docker

| Tool | Image | GPU Support | Platform Notes |
|------|-------|-------------|----------------|
| gnina | `gnina/gnina:latest` | `--gpus all` for CUDA devices | ARM hosts: `--platform linux/amd64` (Rosetta) |
| PostgreSQL | `postgres:16` | N/A | Via `docker-compose.yml` |

Docker is used for gnina (volume mounts map host dirs to `/data/inputs{N}` and output to `/data/output`) and for the PostgreSQL database.

---

## 12. External APIs

### Protein Resolution

| API | Base URL | Returns |
|-----|----------|---------|
| UniProt Search | `rest.uniprot.org/uniprotkb/search` | Accession, gene names, sequence, PDB cross-refs |
| PDBe Best Structures | `ebi.ac.uk/pdbe/graph-api/mappings/best_structures/{uniprot}` | Ranked PDB entries by resolution |
| RCSB PDB Search v2 | `search.rcsb.org/rcsbsearch/v2/query` | PDB IDs matching query |
| RCSB PDB Download | `files.rcsb.org/download/{PDBID}.cif` or `.pdb` | Structure files |
| AlphaFold API | `alphafold.ebi.ac.uk/api/prediction/{uniprot}` | Predicted structure URLs, confidence |
| ESMFold | `api.esmatlas.com/foldSequence/v1/pdb/` | Real-time structure prediction (~400 residues max) |

### Ligand Resolution

| API | Base URL | Returns |
|-----|----------|---------|
| PubChem PUG-REST | `pubchem.ncbi.nlm.nih.gov/rest/pug/` | CIDs, 3D SDF, SMILES, properties (MW, TPSA, LogP, HBD/HBA) |
| RCSB Ligand Expo (CCD) | `files.rcsb.org/ligands/download/{CCD}_ideal.sdf` | Ideal 3D SDF for PDB ligand codes |

### Drug Discovery / Binder Data

| API | Base URL | Returns |
|-----|----------|---------|
| ChEMBL Target | `ebi.ac.uk/chembl/api/data/target.json` | UniProt → ChEMBL target ID |
| ChEMBL Activity | `ebi.ac.uk/chembl/api/data/activity.json` | Bioactive compounds with IC50/Ki/Kd, pChEMBL values |
| ChEMBL Mechanism | `ebi.ac.uk/chembl/api/data/mechanism.json` | Approved drugs with mechanism of action |

### Web Search

| API | Base URL | Auth |
|-----|----------|------|
| Brave Web Search | `api.search.brave.com/res/v1/web/search` | `BRAVE_API_KEY` via `X-Subscription-Token` |

---

## 13. File Formats

### Protein / Structure Formats

| Format | Extensions | Description |
|--------|-----------|-------------|
| PDB | `.pdb` | Legacy protein structure (widely supported) |
| mmCIF | `.cif`, `.mmcif` | Modern structure format (RCSB default) |
| BinaryCIF | `.bcif` | Compressed CIF (smallest/fastest, visualizer only) |
| FASTA | `.fasta`, `.fa` | Amino acid sequence |
| PQR | `.pqr` | Structure with charges and radii (protprep intermediate) |
| PDBQT | `.pdbqt` | AutoDock/gnina receptor/ligand format |

### Ligand / Small Molecule Formats

| Format | Extensions | Description |
|--------|-----------|-------------|
| SDF/MOL | `.sdf`, `.mol` | 3D molecular structure (primary ligand format) |
| MOL2 | `.mol2` | Tripos format with charges |
| PDBQT | `.pdbqt` | AutoDock format with partial charges and torsion info |
| SMILES | `.smi`, inline string | 1D molecular representation |
| XYZ | `.xyz` | Generic 3D coordinates |

### Analysis / Output Formats

| Format | Extensions | Source Tool | Purpose |
|--------|-----------|-------------|---------|
| Confidence JSON | `.json` | Boltz | pLDDT, pTM, ipTM scores |
| Affinity JSON | `.json` | Boltz | Binder probability + affinity value |
| PAE NPZ | `.npz` | Boltz | Predicted Aligned Error matrix |
| XML | `.xml` | PLIP | Machine-parseable interaction report |
| PSE | `.pse` | PLIP | PyMOL session file |
| PNG/SVG | `.png`, `.svg` | PLIP | 2D interaction diagrams |
| MAP/DX/CUBE | `.map`, `.dx`, `.cube` | CCP4/APBS | Volumetric / electron density |

### Envelope / Config Formats

| Format | Extensions | Purpose |
|--------|-----------|---------|
| JSON | `.json` | Result envelopes (`--json-out`), requests |
| YAML | `.yaml`, `.yml` | Human-authored requests (`--request`), result mirror (`--yaml-out`) |
| Markdown | `.md` | Batch manifest summaries (`MANIFEST.md`) |
| CSV | `.csv` | Ligprep input manifests |
| JSONL | `.jsonl`, `.ndjson` | Ligprep input manifests |

---

## 14. Tool ↔ Format Matrix

### Input Formats Accepted

| Tool | PDB | CIF | FASTA | SDF | MOL2 | PDBQT | SMILES | String/Name |
|------|-----|-----|-------|-----|------|-------|--------|-------------|
| bind-boltz | ✓ | ✓ | ✓ (primary) | ✓ | ✓ | — | ✓ | Sequence string |
| bind-gnina | ✓ (receptor) | — | — | ✓ (ligand) | ✓ | ✓ | ✓ | — |
| bind-plip | ✓ | ✓ | — | — | — | — | — | PDB ID |
| bind-posebusters | ✓ | ✓ | — | ✓ (reference) | ✓ (reference) | — | — | — |
| bind-resolve | — | — | — | — | — | — | ✓ | Gene name, drug name, CCD code, CID |
| bind-protprep | ✓ | ✓ | — | — | — | — | — | PDB ID |
| bind-ligprep | — | — | — | ✓ | ✓ | — | ✓ | Name, CID |

### Output Formats Produced

| Tool | PDB | CIF | FASTA | SDF | MOL2 | PDBQT | JSON | YAML | Markdown |
|------|-----|-----|-------|-----|------|-------|------|------|----------|
| bind-boltz | ✓ | ✓ | — | — | — | — | ✓ (confidence, affinity) | ✓ (input) | ✓ (batch) |
| bind-gnina | — | — | — | ✓ (docked poses) | — | — | ✓ (envelope) | ✓ | ✓ (batch) |
| bind-plip | — | — | — | — | — | — | ✓ (envelope) | ✓ | ✓ (batch) |
| bind-posebusters | — | — | — | — | — | — | ✓ (envelope) | ✓ | ✓ (batch) |
| bind-resolve | ✓ | ✓ | ✓ | ✓ | — | — | ✓ (envelope) | ✓ | ✓ (binders) |
| bind-protprep | ✓ | ✓ | — | — | — | — | ✓ (envelope) | ✓ | — |
| bind-ligprep | — | — | — | ✓ | ✓ | ✓ | ✓ (envelope) | ✓ | — |

---

## 15. End-to-End Pipeline Data Flow

The agent executes a 6-step pipeline per protein-ligand hypothesis:

```
Step 1: bind-resolve protein
  Input:  Gene name (string) + organism
  Output: FASTA (.fasta), PDB/CIF (downloaded), binding sites, UniProt data
  APIs:   UniProt → PDBe → RCSB Download / AlphaFold

Step 2: bind-resolve ligand
  Input:  Drug name / SMILES / CCD code / PubChem CID
  Output: SDF 3D (.sdf), molecular properties (MW, LogP, TPSA, HBD/HBA)
  APIs:   PubChem PUG-REST / RCSB CCD / RDKit local generation

Step 3: bind-boltz predict
  Input:  FASTA (.fasta) + SDF (.sdf) or SMILES
  Output: Complex PDB/CIF, confidence JSON, affinity JSON
  Model:  Boltz-2 (diffusion + affinity head)
  GPU:    A100 (Modal) or local CUDA

Step 4: bind-gnina dock
  Input:  Receptor PDB (.pdb) + Ligand SDF (.sdf) + autobox reference
  Output: Multi-model SDF (.sdf) with Vina energy + CNN scores per pose
  Model:  Vina + gnina CNN scorer/affinity predictor
  GPU:    T4 (Modal) or local Docker

Step 5: bind-posebusters check
  Input:  Predicted complex PDB/CIF + optional protein + reference ligand
  Output: Pass/fail per check, categorized failures (fatal/major/minor)
  Engine: PoseBusters rules (RDKit + pandas)

Step 6: bind-plip profile
  Input:  Complex PDB/CIF
  Output: 11 interaction types with counts, interacting residues
  Engine: PLIP library
```

**Frontend composite score:** `Boltz binder_probability (40%) + gnina CNN_score (40%) + PoseBusters pass_rate (20%)`

---

## 16. Environment Variables

### Agent / LLM

| Variable | Purpose |
|----------|---------|
| `BIND_AGENT_API_KEY` | LLM API key (highest priority) |
| `OPENROUTER_API_KEY` | LLM API key (fallback) |
| `BIND_AGENT_BASE_URL` | LLM endpoint base URL |
| `BIND_AGENT_MODEL` / `BIND_TOOLS_MODEL` | LLM model name |

### Compute / Execution

| Variable | Purpose |
|----------|---------|
| `BIND_TOOLS_DEVICE` | Override compute device (`cuda:0`, `cpu`) |
| `BIND_TOOLS_USE_MODAL` | Set to `1` for Modal GPU execution |
| `BIND_TOOLS_API_KEY` | Bearer token for remote REST API auth |
| `REMOTE` | Set to `on`/`1`/`true` for remote REST API dispatch |

### Database

| Variable | Purpose |
|----------|---------|
| `BIND_DB_URL` | PostgreSQL connection string (primary) |
| `DATABASE_URL` | PostgreSQL connection string (fallback) |

### Agent Context (injected into subprocesses)

| Variable | Purpose |
|----------|---------|
| `BIND_AGENT_ID` | Current agent ID (injected into result metadata) |
| `BIND_RUN_ID` | Current run ID (injected into result metadata) |

### Web Search

| Variable | Purpose |
|----------|---------|
| `BRAVE_API_KEY` | Brave Web Search API key |

### Frontend

| Variable | Purpose |
|----------|---------|
| `VITE_API_URL` | Backend API base URL (empty = use Vite proxy) |
| `CORS_ORIGINS` | Allowed CORS origins for API server |

---

## 17. Deployment

### Local Development (`deploy.sh`)

1. Start PostgreSQL via `docker-compose up -d`
2. Install dependencies: `uv pip install -e ".[api,db]"`
3. Start API server: `uvicorn bind_tools.api.app:create_app --factory --port 8000`
4. Start frontend: `cd frontend_SAMPLE && npm run dev` (port 5173)

### Docker Compose (`docker-compose.yml`)

PostgreSQL 16 container:
- Database: `bindops`, user: `bind`, password: `bind`
- Port: 5432, persistent volume: `pgdata`
- Healthcheck: `pg_isready`

### Modal Cloud Deployment

GPU workloads deployed to Modal (`bind-tools-gpu` app):
- Boltz-2 on A100
- gnina on T4
- Search reranker on CPU
- FastAPI gateway on CPU

Remote REST API at `https://benwu408--bind-tools-gpu-webapi-serve.modal.run`

### Endpoints Summary

| Service | URL | Purpose |
|---------|-----|---------|
| Frontend | `http://localhost:5173` | React SPA |
| Backend API | `http://localhost:8000` | FastAPI server |
| Swagger docs | `http://localhost:8000/docs` | Auto-generated API docs |
| Modal GPU API | `https://benwu408--bind-tools-gpu-webapi-serve.modal.run` | Remote GPU execution |
| LLM endpoint | `https://benwu408--gpt-oss-120b-serve.modal.run/v1` | Agent LLM (default) |
