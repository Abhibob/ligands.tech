# Ligands.tech

Computational protein-ligand binding analysis platform. An LLM-driven agent orchestrates a 6-step pipeline — resolve targets, predict structures, dock, and validate — across GPU-accelerated tools, tracking every result in a database and streaming progress to a React frontend.

## How it works

You describe a binding question in natural language ("What drugs bind EGFR?", "Does erlotinib bind TP53?"). The orchestrator agent:

1. **Resolves** protein targets (UniProt, PDB, AlphaFold) and ligands (PubChem, ChEMBL, SMILES)
2. **Predicts** complex structures with Boltz-2 (A100 GPU)
3. **Docks** with gnina CNN scoring (T4 GPU)
4. **Validates** poses with PoseBusters
5. **Profiles** interactions with PLIP
6. **Reports** a scored, evidence-backed summary

For multi-ligand screens, the agent spawns parallel subagents — each running the full pipeline independently — then synthesizes results.

## Architecture

```
                  ┌─────────────┐
                  │   Frontend   │  React + Three.js
                  │  :5173       │  3D molecular viz
                  └──────┬──────┘
                         │ /api
                  ┌──────┴──────┐
                  │  FastAPI     │  Agent mgmt, WebSocket
                  │  :8000       │  events, file serving
                  └──────┬──────┘
                         │
              ┌──────────┴──────────┐
              │   Agent Orchestrator │  LLM-driven loop
              │   (bind-agent)       │  tool calls + subagents
              └──────────┬──────────┘
                         │ subprocess
    ┌────────┬───────┬───┴───┬───────────┬────────┐
    │resolve │ boltz │ gnina │posebusters│  plip  │
    │UniProt │ A100  │  T4   │ rules     │ Python │
    │PubChem │ Modal │ Modal │           │        │
    │ChEMBL  │       │Docker │           │        │
    └────────┴───────┴───────┴───────────┴────────┘
                         │
                    ┌────┴────┐
                    │ Postgres │  Runs, hypotheses,
                    │  :5432   │  pipeline steps,
                    └─────────┘  artifacts
```

## Quick start

```bash
# Prerequisites: Docker, Node.js 18+, Python 3.9-3.12, uv

# 1. Clone and install
git clone https://github.com/Abhibob/cancercurer.git
cd cancercurer
uv pip install -e ".[api,db]"

# 2. Configure
cp .env.example .env
# Edit .env with your API keys

# 3. Launch everything (DB + API + frontend)
./deploy.sh
```

Open **http://localhost:5173** — the frontend connects to the API on `:8000`.

Or run the agent directly from the CLI:

```bash
./run.sh "Analyze binding of erlotinib to EGFR"
```

## CLI tools

Every tool follows the same pattern: run command with `--json-out`, read the structured result envelope.

| Command | Purpose | Upstream |
|---------|---------|----------|
| `bind-resolve` | Protein/ligand/binder resolution | UniProt, PubChem, ChEMBL, RCSB |
| `bind-boltz` | Structure prediction | Boltz-2 (A100 GPU via Modal) |
| `bind-gnina` | Docking + CNN scoring | gnina (T4 GPU or Docker) |
| `bind-posebusters` | Pose validation | PoseBusters Python API |
| `bind-plip` | Interaction profiling | PLIP Python API |
| `bind-memory` | Shared agent memory | Supermemory API / local fallback |
| `bind-qmd` | Local file search | Filesystem |
| `bind-websearch` | Web research | Exa API |

```bash
# Example: resolve a protein, dock a ligand
bind-resolve protein --name EGFR --download-dir proteins/ --json-out results/protein.json
bind-resolve ligand --name erlotinib --download-dir ligands/ --json-out results/ligand.json
bind-gnina dock --receptor proteins/P00533.pdb --ligand ligands/erlotinib.sdf \
  --autobox-ligand ligands/erlotinib.sdf --json-out results/gnina.json
```

All results use the `binding.dev/v1` envelope format with `apiVersion`, `kind`, `metadata`, `summary`, `artifacts`, and `status`.

## Frontend

React 19 SPA with Vite, Tailwind CSS v4, and Three.js for 3D molecular visualization.

| Route | Page |
|-------|------|
| `/` | Landing — prompt input, stats |
| `/agents/:id` | Live agent view — thinking stream, hypothesis cards |
| `/finished/:id` | Completed runs — results replay |
| `/hypothesis/:id` | Single hypothesis — 3D binding viz, score rings, pipeline steps |
| `/results` | Ranked table of all hypotheses |

Composite binding score (0-100) derived from: Boltz binder probability (40%), gnina CNN score (40%), PoseBusters pass rate (20%).

## API

FastAPI server with WebSocket streaming for live agent events.

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/runs` | Spawn an agent run |
| `GET` | `/api/runs/:id` | Poll run status |
| `GET` | `/api/agents` | List agents (filter by status) |
| `GET` | `/api/agents/:id/hypotheses` | Hypotheses with pipeline steps |
| `GET` | `/api/agents/:id/artifacts` | Visualization artifacts |
| `WS` | `/api/agents/:id/ws` | Live event stream |
| `GET` | `/api/artifacts/:path` | Serve workspace files (PDB, SDF, CIF) |

## GPU compute

Heavy compute runs on Modal cloud GPUs. Set `REMOTE=true` in `.env` to enable.

| Tool | GPU | Cost | Cold start |
|------|-----|------|------------|
| Boltz-2 | A100 40GB | ~$3.70/hr | ~30-60s |
| gnina | T4 16GB | ~$0.60/hr | ~15s |

Without Modal, gnina falls back to Docker (`gnina/gnina:latest`) and Boltz runs as a local subprocess.

## Database

PostgreSQL 16 with 5 tables — all operations are idempotent and gracefully degrade (no DB = no tracking, tools still work).

- **agent_runs** — parent/child hierarchy, token counts, status
- **hypotheses** — protein-ligand pair investigations
- **pipeline_steps** — per-step outcomes with confidence JSONB
- **tool_invocations** — CLI call log with inputs/summary/errors
- **viz_artifacts** — file registry (PDB, SDF, CIF paths + metadata)

## Environment variables

| Variable | Purpose |
|----------|---------|
| `BIND_AGENT_API_KEY` | LLM API key |
| `BIND_AGENT_BASE_URL` | LLM endpoint URL |
| `BIND_AGENT_MODEL` | Model identifier |
| `BIND_TOOLS_API_KEY` | Remote GPU API bearer token |
| `REMOTE` | Enable Modal GPU dispatch (`true`/`false`) |
| `BIND_DB_URL` | PostgreSQL connection string |
| `EXA_API_KEY` | Web search API key |
| `SUPERMEMORY_API_KEY` | Shared memory API key (optional) |
| `CORS_ORIGINS` | Allowed CORS origins |
| `VITE_API_URL` | Frontend API base URL |

See `.env.example` for the full template.

## Project structure

```
├── src/bind_tools/
│   ├── agent/          # LLM orchestrator (loop, executor, prompt, tools)
│   ├── api/            # FastAPI server + WebSocket
│   ├── db/             # PostgreSQL tracking
│   ├── common/         # Shared envelope, errors, runner
│   ├── resolve/        # Protein/ligand resolution
│   ├── boltz/          # Boltz-2 wrapper
│   ├── gnina/          # gnina wrapper
│   ├── posebusters/    # PoseBusters wrapper
│   ├── plip/           # PLIP wrapper
│   ├── memory/         # Shared agent memory (Supermemory + local)
│   ├── websearch/      # Web search wrapper
│   ├── qmd/            # Local file search
│   └── modal_app/      # Modal GPU deployment
├── frontend_SAMPLE/    # React SPA
├── binding_agent_spec/ # Agent prompts, skills, schemas
├── deploy.sh           # One-command platform launcher
├── run.sh              # One-command agent runner
├── docker-compose.yml  # PostgreSQL
└── pyproject.toml      # Python project config
```

## Development

```bash
# Install dev dependencies
uv pip install -e ".[dev]"

# Run tests
pytest

# Lint
ruff check src/

# Run individual tools
bind-resolve doctor
bind-gnina doctor
bind-boltz doctor
```

## Acknowledgments

Built by [Abhinav Raja](https://github.com/Abhibob), [Ben Wu](https://github.com/benwu408), [Scott Oftedahl](https://github.com/scottyoftedahl), and [Chandhra Gundam](https://github.com/cmrcode99).
Development assisted by [Claude Code](https://claude.ai/claude-code) (Anthropic) and [Codex](https://openai.com/codex) (OpenAI).
