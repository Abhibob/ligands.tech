# Implementation Plan: Binding Agent CLI Tools

## Overview

Build 5 CLI wrapper tools (`bind-boltz`, `bind-gnina`, `bind-posebusters`, `bind-plip`, `bind-qmd`) as a single Python package using Typer, Pydantic, and uv. Each wrapper follows the contracts defined in `binding_agent_spec/`.

## Project Structure

```
cancercurer/
├── binding_agent_spec/          # existing specs (unchanged)
├── pyproject.toml               # single package: bind-tools
├── src/
│   └── bind_tools/
│       ├── __init__.py
│       ├── _version.py          # "0.1.0"
│       ├── common/
│       │   ├── __init__.py
│       │   ├── envelope.py      # base Pydantic models for request/result envelopes
│       │   ├── cli_base.py      # shared Typer callbacks (--json-out, --yaml-out, etc.)
│       │   ├── runner.py        # subprocess + Docker runner utilities
│       │   └── errors.py        # exit codes, BindToolError hierarchy
│       ├── boltz/
│       │   ├── __init__.py
│       │   ├── cli.py           # Typer app: bind-boltz predict|doctor|schema
│       │   ├── models.py        # BoltzPredictRequest, BoltzPredictResult (Pydantic)
│       │   └── runner.py        # translates request → boltz CLI call → parses output
│       ├── gnina/
│       │   ├── __init__.py
│       │   ├── cli.py           # Typer app: bind-gnina dock|score|minimize|doctor|schema
│       │   ├── models.py        # GninaDockRequest, GninaScoreRequest, etc.
│       │   └── runner.py        # translates request → docker run gnina → parses SDF output
│       ├── posebusters/
│       │   ├── __init__.py
│       │   ├── cli.py           # Typer app: bind-posebusters check|doctor|schema
│       │   ├── models.py        # PoseBustersCheckRequest, PoseBustersCheckResult
│       │   └── runner.py        # calls posebusters Python API directly
│       ├── plip/
│       │   ├── __init__.py
│       │   ├── cli.py           # Typer app: bind-plip profile|doctor|schema
│       │   ├── models.py        # PlipProfileRequest, PlipProfileResult
│       │   └── runner.py        # calls PLIP Python API directly
│       └── qmd/
│           ├── __init__.py
│           ├── cli.py           # Typer app: bind-qmd query|get|update|doctor|schema
│           ├── models.py        # QmdQueryRequest, QmdQueryResult
│           └── runner.py        # keyword/glob search over local Markdown/JSON files
└── tests/
    ├── conftest.py              # shared fixtures (tmp_path factories, sample files)
    ├── test_envelope.py         # test common envelope validation
    ├── test_boltz.py            # test boltz request validation, result parsing, dry-run
    ├── test_gnina.py            # test gnina request validation, SDF parsing, Docker cmd gen
    ├── test_posebusters.py      # test posebusters request validation, DataFrame→result
    ├── test_plip.py             # test plip request validation, interaction parsing
    └── test_qmd.py              # test qmd keyword search, collection loading
```

## pyproject.toml Entry Points

```toml
[project.scripts]
bind-boltz = "bind_tools.boltz.cli:app"
bind-gnina = "bind_tools.gnina.cli:app"
bind-posebusters = "bind_tools.posebusters.cli:app"
bind-plip = "bind_tools.plip.cli:app"
bind-qmd = "bind_tools.qmd.cli:app"
```

## Dependencies

```
python = ">=3.11,<3.13"
typer = ">=0.9"
pydantic = ">=2.0"
pyyaml = ">=6.0"
rich = ">=13.0"           # pretty console output

# Tool-specific (optional groups):
boltz = ">=1.0"           # Boltz-2 (pulls PyTorch, etc.)
posebusters = ">=0.2"     # PoseBusters (pulls RDKit, pandas)
plip = ">=2.3"            # PLIP (requires openbabel)
rdkit                     # needed for gnina SDF parsing
```

## GPU / CUDA Policy

- All wrappers accept `--device <string>` (e.g., `cuda:0`, `cpu`)
- Default: auto-detect via `torch.cuda.is_available()` where relevant
- gnina Docker: pass `--gpus all` when device != "cpu", omit when `--no-gpu` or device == "cpu"
- boltz: pass `--accelerator gpu` or `--accelerator cpu` based on device flag
- Environment variable `BIND_TOOLS_DEVICE` can override the default globally

## Implementation Order (sequential, each tested before moving on)

### Step 1: Scaffold + Common Layer
- Create `pyproject.toml` with uv
- Build `common/envelope.py` — base Pydantic models matching `common-envelope.schema.json`
- Build `common/cli_base.py` — shared Typer options (--json-out, --yaml-out, --request, etc.)
- Build `common/runner.py` — subprocess runner, Docker runner, timeout handling
- Build `common/errors.py` — exit code constants, error classes
- **Test**: validate envelope serialization matches JSON schema

### Step 2: bind-qmd (simplest tool, no external deps)
- Pydantic models from `qmd-query.schema.json` / `qmd-result.schema.json`
- Runner: keyword search over local files using glob + regex (no vector DB needed)
- CLI: `bind-qmd query --text "..." --kind skill --top-k 5 --json-out out.json`
- Subcommands: `query`, `get`, `doctor`, `schema`
- **Test**: query for "boltz skill" returns the right SKILL.md path

### Step 3: bind-posebusters (Python API, no subprocess)
- Pydantic models from `posebusters-request/result.schema.json`
- Runner: import posebusters, call `PoseBusters(config=...).bust(...)`, convert DataFrame → result model
- Categorize failures into fatal/major/minor per spec
- CLI: `bind-posebusters check --request req.yaml --json-out out.json`
- **Test**: validate a known-good and known-bad SDF, check categorization

### Step 4: bind-plip (Python API, no subprocess)
- Pydantic models from `plip-request/result.schema.json`
- Runner: import plip, use `PDBComplex().load_pdb()` + `.analyze()`, extract interactions
- Map interaction types → normalized counts and residue lists
- CLI: `bind-plip profile --complex file.pdb --json-out out.json`
- **Test**: profile a known complex, check interaction counts

### Step 5: bind-gnina (Docker, SDF parsing)
- Pydantic models from `gnina-*-request.schema.json` / `gnina-result.schema.json`
- Runner: build `docker run gnina/gnina ...` command, execute, parse output SDF with RDKit
- Extract CNNscore, CNNaffinity, minimizedAffinity from SD properties
- Handle `--gpus all` when CUDA available, `--no_gpu` when not
- CLI: `bind-gnina dock|score|minimize --receptor r.pdb --ligand l.sdf --json-out out.json`
- **Test**: validate command generation (dry-run), test SDF parsing with mock output

### Step 6: bind-boltz (subprocess, most complex)
- Pydantic models from `boltz2-request/result.schema.json`
- Runner: translate house request → upstream Boltz YAML format, call `boltz predict`, parse output CIF + confidence JSON + affinity JSON
- Handle MSA server, constraints, pocket residues
- CLI: `bind-boltz predict --request req.yaml --json-out out.json`
- **Test**: validate request translation, test result parsing with mock Boltz output

### Step 7: Integration tests
- End-to-end dry-run tests for all wrappers
- Schema validation: every emitted result validates against the JSON schemas in `binding_agent_spec/schemas/`
- Doctor command tests for each wrapper

## Key Design Decisions

1. **Single package, multiple entry points** — simpler to install and version than 5 separate packages
2. **Pydantic v2 models mirror JSON schemas exactly** — field names use camelCase aliases to match schema conventions
3. **Docker for gnina only** — boltz/posebusters/plip are pip-installable Python packages
4. **Dry-run mode** for every wrapper — validates request and prints the resolved command without executing
5. **Request file OR flags** — both paths converge to the same Pydantic model before execution
6. **Result envelope always written** even on failure — `status: "failed"` with errors populated
