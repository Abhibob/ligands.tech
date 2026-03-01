# Building the Supermemory Layer for BindingOps

## What You're Building

You're building the **shared memory infrastructure** that lets BindingOps subagents communicate with each other. When the orchestrator spawns 5 parallel Boltz screening subagents, they each write their findings to Supermemory. When a PoseBusters subagent needs the pose path from a Boltz run, it searches Supermemory. When the orchestrator needs to synthesize a final answer, it pulls a profile of the entire run.

Your layer sits between the LLM agents and the Supermemory API (or local Markdown fallback). It has three responsibilities:

1. **A Python client** wrapping the Supermemory REST API with BindingOps-specific conventions
2. **Tool definitions** that get injected into every subagent's tool list
3. **A local fallback** for when `SUPERMEMORY_API_KEY` isn't set

---

## Architecture Within the Project

```
src/bind_tools/
├── common/
│   └── ...                    # existing common layer (your teammates)
├── memory/                    # ← YOUR MODULE
│   ├── __init__.py
│   ├── client.py              # SupermemoryClient — thin wrapper around the API
│   ├── local_fallback.py      # LocalMemoryClient — Markdown workspace fallback
│   ├── facade.py              # MemoryFacade — routes to hosted or local based on env
│   ├── models.py              # Pydantic models for memory operations
│   ├── tool_defs.py           # OpenRouter-compatible tool JSON definitions
│   └── conventions.py         # containerTag patterns, metadata schemas, customId patterns
├── boltz/
├── gnina/
├── posebusters/
├── plip/
└── qmd/
```

---

## Step 1: Pydantic Models (`models.py`)

Define the data contracts first. These mirror what the Supermemory API expects and returns, but typed for your codebase.

```python
from __future__ import annotations
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


# ── Inputs ──

class MemoryAddInput(BaseModel):
    """What an agent passes when calling memory_add."""
    content: str = Field(..., description="Markdown-formatted findings")
    container_tag: str = Field(..., description="Run scope, e.g. 'run-20260227-001'")
    custom_id: Optional[str] = Field(
        None, description="Idempotency key, e.g. 'boltz-findings-ligand-a'"
    )
    metadata: Optional[dict] = Field(
        None, description="Filterable key-values: tool, stage, target, scores"
    )
    entity_context: Optional[str] = Field(
        None,
        max_length=1500,
        description="Extraction hint for Supermemory's memory generator",
    )


class MemorySearchInput(BaseModel):
    """What an agent passes when calling memory_search."""
    query: str
    container_tag: Optional[str] = None
    filters: Optional[dict] = None
    limit: int = 10
    search_mode: str = Field(
        "hybrid", description="'hybrid' or 'memories'"
    )


class MemoryProfileInput(BaseModel):
    """What an agent passes when calling memory_profile."""
    container_tag: str
    query: Optional[str] = None


# ── Outputs ──

class MemoryAddResult(BaseModel):
    id: str
    status: str  # "queued", "processing", "done"


class SearchHit(BaseModel):
    id: str
    memory: Optional[str] = None
    chunk: Optional[str] = None
    similarity: Optional[float] = None
    metadata: Optional[dict] = None
    updated_at: Optional[str] = None


class MemorySearchResult(BaseModel):
    results: list[SearchHit]
    total: int
    timing_ms: Optional[int] = None


class ProfileData(BaseModel):
    static: list[str] = []
    dynamic: list[str] = []


class MemoryProfileResult(BaseModel):
    profile: ProfileData
    search_results: Optional[MemorySearchResult] = None
```

---

## Step 2: Supermemory Client (`client.py`)

This is a thin async wrapper around the three endpoints you need. Use `httpx` for async HTTP.

```python
import httpx
import os
from .models import (
    MemoryAddInput, MemoryAddResult,
    MemorySearchInput, MemorySearchResult,
    MemoryProfileInput, MemoryProfileResult, ProfileData, SearchHit,
)

API_BASE = "https://api.supermemory.ai"


class SupermemoryClient:
    """Thin wrapper around the Supermemory REST API."""

    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or os.environ.get("SUPERMEMORY_API_KEY")
        if not self.api_key:
            raise ValueError("SUPERMEMORY_API_KEY not set")
        self._headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    # ── Add ──

    async def add(self, inp: MemoryAddInput) -> MemoryAddResult:
        payload: dict = {
            "content": inp.content,
            "containerTag": inp.container_tag,
        }
        if inp.custom_id:
            payload["customId"] = inp.custom_id
        if inp.metadata:
            payload["metadata"] = inp.metadata
        if inp.entity_context:
            payload["entityContext"] = inp.entity_context

        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{API_BASE}/v3/documents",
                headers=self._headers,
                json=payload,
                timeout=30,
            )
            resp.raise_for_status()
            data = resp.json()
            return MemoryAddResult(id=data["id"], status=data.get("status", "queued"))

    # ── Search ──

    async def search(self, inp: MemorySearchInput) -> MemorySearchResult:
        # Use /v3/search for document search (takes containerTags as array)
        payload: dict = {"q": inp.query, "limit": inp.limit}
        if inp.container_tag:
            payload["containerTags"] = [inp.container_tag]
        if inp.filters:
            payload["filters"] = inp.filters

        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{API_BASE}/v3/search",
                headers=self._headers,
                json=payload,
                timeout=30,
            )
            resp.raise_for_status()
            data = resp.json()
            hits = [
                SearchHit(
                    id=r.get("id", ""),
                    memory=r.get("memory"),
                    chunk=r.get("chunk"),
                    similarity=r.get("similarity"),
                    metadata=r.get("metadata"),
                    updated_at=r.get("updatedAt"),
                )
                for r in data.get("results", [])
            ]
            return MemorySearchResult(
                results=hits,
                total=data.get("total", len(hits)),
                timing_ms=data.get("timing"),
            )

    # ── Profile ──

    async def profile(self, inp: MemoryProfileInput) -> MemoryProfileResult:
        payload: dict = {"containerTag": inp.container_tag}
        if inp.query:
            payload["q"] = inp.query

        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{API_BASE}/v4/profile",
                headers=self._headers,
                json=payload,
                timeout=30,
            )
            resp.raise_for_status()
            data = resp.json()

            prof = data.get("profile", {})
            profile_data = ProfileData(
                static=prof.get("static", []),
                dynamic=prof.get("dynamic", []),
            )

            search_results = None
            if "searchResults" in data:
                sr = data["searchResults"]
                hits = [
                    SearchHit(
                        id=r.get("id", ""),
                        memory=r.get("memory"),
                        chunk=r.get("chunk"),
                        similarity=r.get("similarity"),
                        metadata=r.get("metadata"),
                    )
                    for r in sr.get("results", [])
                ]
                search_results = MemorySearchResult(
                    results=hits,
                    total=sr.get("total", len(hits)),
                    timing_ms=sr.get("timing"),
                )

            return MemoryProfileResult(
                profile=profile_data, search_results=search_results
            )
```

### Key Supermemory API Details

**Endpoints you use:**

| Operation | Endpoint | Key fields |
|-----------|----------|------------|
| Add document | `POST /v3/documents` | `content`, `containerTag`, `customId`, `metadata`, `entityContext` |
| Search | `POST /v3/search` | `q`, `containerTags` (array!), `filters`, `limit` |
| Profile | `POST /v4/profile` | `containerTag` (string!), `q` (optional) |

**Watch out for:**
- `/v3/search` takes `containerTags` as an **array**: `["run-001"]`
- `/v4/profile` takes `containerTag` as a **string**: `"run-001"`
- Metadata values must be **flat** — strings, numbers, booleans only, no nested objects
- `customId` enables idempotent updates — same ID overwrites the previous version
- Supermemory processes documents asynchronously; `add()` returns `"queued"` immediately
- Filters must be wrapped in `AND` or `OR` arrays (see filter structure below)

**Filter structure for numeric scores:**
```python
filters = {
    "AND": [
        {"key": "tool", "value": "boltz", "negate": False},
        {
            "filterType": "numeric",
            "key": "binder_probability",
            "value": "0.7",
            "numericOperator": ">=",
            "negate": False,
        },
    ]
}
```

---

## Step 3: Local Markdown Fallback (`local_fallback.py`)

When `SUPERMEMORY_API_KEY` is unset, memory degrades to file-based storage. This is functional but loses semantic search — you get keyword matching only.

```python
import os
import re
import json
from pathlib import Path
from datetime import datetime, timezone
from .models import (
    MemoryAddInput, MemoryAddResult,
    MemorySearchInput, MemorySearchResult, SearchHit,
    MemoryProfileInput, MemoryProfileResult, ProfileData,
)

WORKSPACE_ROOT = os.environ.get("BIND_TOOLS_WORKSPACE", "./workspace")


class LocalMemoryClient:
    """Markdown-based fallback when Supermemory is unavailable."""

    def _run_dir(self, container_tag: str) -> Path:
        d = Path(WORKSPACE_ROOT) / container_tag
        d.mkdir(parents=True, exist_ok=True)
        (d / "findings").mkdir(exist_ok=True)
        return d

    async def add(self, inp: MemoryAddInput) -> MemoryAddResult:
        run_dir = self._run_dir(inp.container_tag)

        # Determine filename
        if inp.custom_id:
            safe_id = re.sub(r"[^a-zA-Z0-9_\-]", "_", inp.custom_id)
            filepath = run_dir / "findings" / f"{safe_id}.md"
        else:
            ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
            filepath = run_dir / "findings" / f"{ts}.md"

        # Write content with metadata frontmatter
        lines = ["---"]
        if inp.metadata:
            for k, v in inp.metadata.items():
                lines.append(f"{k}: {v}")
        lines.append(f"created_at: {datetime.now(timezone.utc).isoformat()}")
        lines.append("---\n")
        lines.append(inp.content)

        filepath.write_text("\n".join(lines), encoding="utf-8")

        # Also append to the shared log
        log = run_dir / "log.md"
        with open(log, "a", encoding="utf-8") as f:
            ts = datetime.now(timezone.utc).isoformat()
            f.write(f"\n## [{ts}] {inp.custom_id or 'anonymous'}\n\n")
            summary = inp.content[:200].replace("\n", " ")
            f.write(f"{summary}...\n")

        return MemoryAddResult(id=str(filepath), status="done")

    async def search(self, inp: MemorySearchInput) -> MemorySearchResult:
        """Keyword search across all .md and .json files in the workspace."""
        hits: list[SearchHit] = []
        search_dir = Path(WORKSPACE_ROOT)
        if inp.container_tag:
            search_dir = search_dir / inp.container_tag

        if not search_dir.exists():
            return MemorySearchResult(results=[], total=0)

        query_terms = inp.query.lower().split()

        for fpath in search_dir.rglob("*.md"):
            try:
                text = fpath.read_text(encoding="utf-8")
            except Exception:
                continue

            text_lower = text.lower()
            matched = sum(1 for t in query_terms if t in text_lower)
            if matched == 0:
                continue

            score = matched / len(query_terms)

            # Extract a snippet around the first match
            snippet = ""
            for term in query_terms:
                idx = text_lower.find(term)
                if idx >= 0:
                    start = max(0, idx - 80)
                    end = min(len(text), idx + 120)
                    snippet = text[start:end].replace("\n", " ")
                    break

            # Extract metadata from YAML frontmatter
            meta = {}
            if text.startswith("---"):
                end_idx = text.find("---", 3)
                if end_idx > 0:
                    for line in text[3:end_idx].strip().split("\n"):
                        if ":" in line:
                            k, v = line.split(":", 1)
                            meta[k.strip()] = v.strip()

            hits.append(SearchHit(
                id=str(fpath),
                memory=snippet,
                chunk=snippet,
                similarity=score,
                metadata=meta if meta else None,
            ))

        # Sort by score descending, take top N
        hits.sort(key=lambda h: h.similarity or 0, reverse=True)
        hits = hits[: inp.limit]

        return MemorySearchResult(results=hits, total=len(hits))

    async def profile(self, inp: MemoryProfileInput) -> MemoryProfileResult:
        """Build a rough profile from workspace files."""
        run_dir = self._run_dir(inp.container_tag)

        static: list[str] = []
        dynamic: list[str] = []

        # Read plan.md for static facts
        plan = run_dir / "plan.md"
        if plan.exists():
            for line in plan.read_text().split("\n"):
                line = line.strip()
                if line.startswith("- ") or line.startswith("* "):
                    static.append(line[2:])

        # Read recent findings for dynamic context
        findings_dir = run_dir / "findings"
        if findings_dir.exists():
            files = sorted(findings_dir.glob("*.md"), key=os.path.getmtime, reverse=True)
            for f in files[:5]:
                text = f.read_text(encoding="utf-8")
                # Take first non-frontmatter line as summary
                in_frontmatter = False
                for line in text.split("\n"):
                    if line.strip() == "---":
                        in_frontmatter = not in_frontmatter
                        continue
                    if not in_frontmatter and line.strip():
                        dynamic.append(line.strip()[:200])
                        break

        search_results = None
        if inp.query:
            search_results = await self.search(
                MemorySearchInput(
                    query=inp.query,
                    container_tag=inp.container_tag,
                    limit=5,
                )
            )

        return MemoryProfileResult(
            profile=ProfileData(static=static, dynamic=dynamic),
            search_results=search_results,
        )
```

### Fallback Workspace Layout

```
workspace/
└── run-20260227-001/
    ├── plan.md               # orchestrator writes execution plan
    ├── log.md                # append-only event log
    ├── findings/
    │   ├── boltz-findings-ligand-a.md
    │   ├── pb-check-ligand-a.md
    │   ├── gnina-score-ligand-a.md
    │   └── plip-profile-ligand-a.md
    └── consensus.md          # orchestrator's final synthesis
```

---

## Step 4: Facade (`facade.py`)

The facade auto-selects hosted vs. local based on environment. This is the single entry point the rest of the codebase uses.

```python
import os
from .models import (
    MemoryAddInput, MemoryAddResult,
    MemorySearchInput, MemorySearchResult,
    MemoryProfileInput, MemoryProfileResult,
)


class MemoryFacade:
    """Routes memory calls to Supermemory API or local fallback."""

    def __init__(self):
        api_key = os.environ.get("SUPERMEMORY_API_KEY")
        if api_key:
            from .client import SupermemoryClient
            self._backend = SupermemoryClient(api_key)
            self.backend_name = "supermemory"
        else:
            from .local_fallback import LocalMemoryClient
            self._backend = LocalMemoryClient()
            self.backend_name = "local"

    async def add(self, inp: MemoryAddInput) -> MemoryAddResult:
        return await self._backend.add(inp)

    async def search(self, inp: MemorySearchInput) -> MemorySearchResult:
        return await self._backend.search(inp)

    async def profile(self, inp: MemoryProfileInput) -> MemoryProfileResult:
        return await self._backend.profile(inp)
```

---

## Step 5: Conventions (`conventions.py`)

This is where you codify the BindingOps-specific patterns so every part of the system uses consistent container tags, metadata keys, and customId formats.

```python
"""BindingOps memory conventions.

These patterns are used by the orchestrator and subagents to ensure
consistent scoping, filtering, and idempotent updates.
"""

from datetime import datetime, timezone


# ── Container Tag Patterns ──

def run_tag(run_id: str) -> str:
    """Single-run isolation. Most common scope."""
    return f"run-{run_id}"

def project_tag(project_name: str) -> str:
    """Cross-run scope for a campaign (e.g. 'egfr-campaign')."""
    return f"project-{project_name}"

GLOBAL_TAG = "global-knowledge"


# ── Custom ID Patterns ──
# These enable idempotent updates: same customId → overwrites previous.

def findings_id(tool: str, ligand_id: str) -> str:
    """e.g. 'boltz-findings-ligand_a'"""
    return f"{tool}-findings-{ligand_id}"

def plan_id(run_id: str) -> str:
    return f"plan-{run_id}"

def consensus_id(run_id: str) -> str:
    return f"consensus-{run_id}"


# ── Standard Metadata Keys ──
# Metadata values must be flat: str | int | float | bool only.

TOOL_KEY = "tool"           # "boltz", "gnina", "posebusters", "plip"
STAGE_KEY = "stage"         # "screening", "validation", "rescoring", "profiling", "consensus"
TARGET_KEY = "target"       # protein name, e.g. "EGFR"
LIGAND_ID_KEY = "ligand_id"
AGENT_ID_KEY = "agent_id"

# Numeric score keys (filterable with numericOperator)
BINDER_PROB_KEY = "binder_probability"
AFFINITY_KEY = "affinity_value"
CNN_SCORE_KEY = "cnn_score"
CNN_AFFINITY_KEY = "cnn_affinity"
PB_PASS_KEY = "pb_all_pass"  # 1 or 0


# ── Entity Context Templates ──
# Guides Supermemory's memory extraction for each tool type.

ENTITY_CONTEXTS = {
    "boltz": (
        "Boltz-2 structure prediction and binding affinity result. "
        "Extract: binder probability, affinity value, pose path, target protein, "
        "ligand identifier, confidence metrics (pLDDT, ipTM), and any warnings."
    ),
    "posebusters": (
        "PoseBusters pose plausibility check result. "
        "Extract: pass/fail verdict, categorized failures (fatal/major/minor), "
        "target protein, ligand identifier, and which specific checks failed."
    ),
    "gnina": (
        "gnina docking/scoring/minimization result. "
        "Extract: CNNscore, CNNaffinity, minimizedAffinity, mode (dock/score/minimize), "
        "target protein, ligand identifier, and number of poses generated."
    ),
    "plip": (
        "PLIP protein-ligand interaction profile. "
        "Extract: interaction counts by type (H-bonds, hydrophobic, pi-stacking, "
        "salt bridges, etc.), key interacting residues, target protein, ligand identifier."
    ),
}
```

---

## Step 6: Tool Definitions for Agents (`tool_defs.py`)

These are the OpenRouter function-calling tool definitions injected into every subagent. The orchestrator's `spawn_subagent` includes these in the `tools` array.

```python
"""OpenRouter-compatible tool definitions for agent memory operations."""

MEMORY_ADD_TOOL = {
    "type": "function",
    "function": {
        "name": "memory_add",
        "description": (
            "Store a finding, result, or note in shared memory. Other agents "
            "can search for it later. Use this to record tool outputs, intermediate "
            "results, research findings, or any context that should persist beyond "
            "your conversation. Write Markdown. Include key metrics, file paths, "
            "and your interpretation."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "content": {
                    "type": "string",
                    "description": (
                        "The content to store. Markdown preferred. Include key "
                        "metrics, file paths, and your interpretation."
                    ),
                },
                "container_tag": {
                    "type": "string",
                    "description": (
                        "Scope tag, typically the run ID "
                        "(e.g., 'run-20260227-001')"
                    ),
                },
                "custom_id": {
                    "type": "string",
                    "description": (
                        "Unique ID for this memory (e.g., "
                        "'boltz-findings-ligand-a'). Using the same ID again "
                        "will update the existing memory."
                    ),
                },
                "metadata": {
                    "type": "object",
                    "description": (
                        "Key-value pairs for filtering. Use for: tool name, "
                        "stage, target, ligand_id, numeric scores like "
                        "binder_probability and cnn_score."
                    ),
                },
            },
            "required": ["content", "container_tag"],
        },
    },
}

MEMORY_SEARCH_TOOL = {
    "type": "function",
    "function": {
        "name": "memory_search",
        "description": (
            "Search shared memory for findings from other agents, prior "
            "results, or stored context. Use this instead of assuming context "
            "is in your conversation — other agents' work is only accessible "
            "through memory search."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Natural language search query",
                },
                "container_tag": {
                    "type": "string",
                    "description": "Scope to a specific run or project",
                },
                "filters": {
                    "type": "object",
                    "description": (
                        "Metadata filters. Wrap in AND/OR arrays. "
                        "Supports keys: tool, stage, target, ligand_id, "
                        "and numeric comparisons on scores."
                    ),
                },
                "limit": {
                    "type": "integer",
                    "default": 10,
                },
            },
            "required": ["query"],
        },
    },
}

MEMORY_PROFILE_TOOL = {
    "type": "function",
    "function": {
        "name": "memory_profile",
        "description": (
            "Get an aggregated profile of a run or project. Returns static "
            "facts and dynamic recent context. Use for a quick overview "
            "before diving into specific searches."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "container_tag": {
                    "type": "string",
                    "description": "Run or project ID",
                },
                "query": {
                    "type": "string",
                    "description": (
                        "Optional query to also return relevant search "
                        "results alongside the profile"
                    ),
                },
            },
            "required": ["container_tag"],
        },
    },
}


ALL_MEMORY_TOOLS = [MEMORY_ADD_TOOL, MEMORY_SEARCH_TOOL, MEMORY_PROFILE_TOOL]
```

---

## Step 7: Tool Executor (Connecting Tool Calls to the Facade)

When a subagent makes a tool call like `memory_add(...)`, something needs to parse the arguments and call your facade. This goes in the orchestrator loop, but you provide the handler:

```python
# memory/executor.py
import json
from .facade import MemoryFacade
from .models import MemoryAddInput, MemorySearchInput, MemoryProfileInput


class MemoryToolExecutor:
    """Handles memory tool calls from LLM agents."""

    def __init__(self, facade: MemoryFacade | None = None):
        self.facade = facade or MemoryFacade()

    async def execute(self, tool_name: str, arguments: str | dict) -> str:
        """Execute a memory tool call. Returns JSON string for the tool response."""
        if isinstance(arguments, str):
            arguments = json.loads(arguments)

        if tool_name == "memory_add":
            inp = MemoryAddInput(**arguments)
            result = await self.facade.add(inp)
            return result.model_dump_json()

        elif tool_name == "memory_search":
            inp = MemorySearchInput(**arguments)
            result = await self.facade.search(inp)
            return result.model_dump_json()

        elif tool_name == "memory_profile":
            inp = MemoryProfileInput(**arguments)
            result = await self.facade.profile(inp)
            return result.model_dump_json()

        else:
            return json.dumps({"error": f"Unknown memory tool: {tool_name}"})
```

The orchestrator's agent loop would use it like:

```python
# In the orchestrator's tool dispatch (your teammate's code)
from bind_tools.memory.executor import MemoryToolExecutor
from bind_tools.memory.tool_defs import ALL_MEMORY_TOOLS

memory_executor = MemoryToolExecutor()

# When building the OpenRouter request, include the tools:
tools = [run_cli_tool, spawn_subagent_tool] + ALL_MEMORY_TOOLS

# When handling tool_calls from the LLM response:
for tool_call in response.choices[0].message.tool_calls:
    name = tool_call.function.name
    args = tool_call.function.arguments

    if name.startswith("memory_"):
        result_json = await memory_executor.execute(name, args)
        # Feed result_json back as the tool response message
```

---

## Step 8: Testing

### Unit tests for the local fallback (no API key needed)

```python
# tests/test_memory_local.py
import pytest
from bind_tools.memory.local_fallback import LocalMemoryClient
from bind_tools.memory.models import MemoryAddInput, MemorySearchInput

@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("BIND_TOOLS_WORKSPACE", str(tmp_path))
    return LocalMemoryClient()

@pytest.mark.asyncio
async def test_add_and_search(client):
    await client.add(MemoryAddInput(
        content="# Boltz Result\nbinder probability: 0.92",
        container_tag="run-test-001",
        custom_id="boltz-findings-lig1",
        metadata={"tool": "boltz", "binder_probability": 0.92},
    ))

    results = await client.search(MemorySearchInput(
        query="boltz binder probability",
        container_tag="run-test-001",
    ))
    assert len(results.results) >= 1
    assert "0.92" in (results.results[0].memory or results.results[0].chunk or "")

@pytest.mark.asyncio
async def test_idempotent_update(client):
    """Same custom_id should overwrite."""
    await client.add(MemoryAddInput(
        content="version 1",
        container_tag="run-test-002",
        custom_id="my-doc",
    ))
    await client.add(MemoryAddInput(
        content="version 2",
        container_tag="run-test-002",
        custom_id="my-doc",
    ))
    results = await client.search(MemorySearchInput(
        query="version",
        container_tag="run-test-002",
    ))
    # Should only find version 2
    texts = " ".join(h.memory or h.chunk or "" for h in results.results)
    assert "version 2" in texts
```

### Integration test with real Supermemory (optional, needs API key)

```python
# tests/test_memory_hosted.py
import os, pytest
from bind_tools.memory.client import SupermemoryClient
from bind_tools.memory.models import MemoryAddInput, MemorySearchInput

pytestmark = pytest.mark.skipif(
    not os.environ.get("SUPERMEMORY_API_KEY"),
    reason="SUPERMEMORY_API_KEY not set"
)

@pytest.fixture
def client():
    return SupermemoryClient()

@pytest.mark.asyncio
async def test_roundtrip(client):
    result = await client.add(MemoryAddInput(
        content="Integration test: binder probability 0.85 for test ligand",
        container_tag="test-integration",
        custom_id="integration-test-doc",
        metadata={"tool": "test", "binder_probability": 0.85},
    ))
    assert result.status in ("queued", "processing", "done")
    # Note: search may not find it immediately due to async processing
```

### Test the facade routing

```python
# tests/test_memory_facade.py
import pytest
from bind_tools.memory.facade import MemoryFacade

def test_selects_local_when_no_key(monkeypatch):
    monkeypatch.delenv("SUPERMEMORY_API_KEY", raising=False)
    facade = MemoryFacade()
    assert facade.backend_name == "local"

def test_selects_supermemory_when_key_set(monkeypatch):
    monkeypatch.setenv("SUPERMEMORY_API_KEY", "test-key")
    facade = MemoryFacade()
    assert facade.backend_name == "supermemory"
```

---

## How It All Flows Together

Here's the concrete data flow for "Does erlotinib bind EGFR?":

```
Orchestrator
│
├─ memory_add(content="Plan: predict EGFR+erlotinib binding",
│             container_tag="run-001",
│             custom_id="plan-run-001",
│             metadata={stage: "planning", target: "EGFR"})
│
├─ spawn_subagent(task="Run bind-boltz predict...")
│   │
│   └─ Boltz subagent:
│       ├─ run_cli("bind-boltz predict ...")
│       └─ memory_add(
│            content="# Boltz Findings\n- binder_prob: 0.92\n- pose: /artifacts/boltz/model_0.cif",
│            container_tag="run-001",
│            custom_id="boltz-findings-erlotinib",
│            metadata={tool: "boltz", target: "EGFR", ligand_id: "erlotinib",
│                      binder_probability: 0.92, affinity_value: -7.2})
│
├─ spawn_subagent(task="Run bind-posebusters on boltz pose")
│   │
│   └─ PB subagent:
│       ├─ memory_search(query="boltz pose path erlotinib", container_tag="run-001")
│       │   → finds: /artifacts/boltz/model_0.cif
│       ├─ run_cli("bind-posebusters check ...")
│       └─ memory_add(
│            content="# PoseBusters\n- all checks pass\n- no fatal/major failures",
│            container_tag="run-001",
│            custom_id="pb-check-erlotinib",
│            metadata={tool: "posebusters", ligand_id: "erlotinib", pb_all_pass: 1})
│
├─ (gnina and plip subagents follow same pattern)
│
└─ Orchestrator:
    ├─ memory_search(query="all findings erlotinib", container_tag="run-001")
    ├─ memory_profile(container_tag="run-001", query="binding evidence")
    └─ Synthesizes consensus answer
```

---

## Dependencies to Add to pyproject.toml

```toml
[project]
dependencies = [
    # ... existing deps ...
    "httpx>=0.27",           # async HTTP for Supermemory API
]
```

No new optional dependency groups needed — `httpx` is lightweight and always installed. The local fallback uses only stdlib + Pydantic (already a dependency).

---

## Summary Checklist

| # | Task | Status |
|---|------|--------|
| 1 | `models.py` — Pydantic models for add/search/profile I/O | |
| 2 | `client.py` — async httpx wrapper for Supermemory REST API | |
| 3 | `local_fallback.py` — Markdown workspace fallback | |
| 4 | `facade.py` — auto-routing facade | |
| 5 | `conventions.py` — containerTag patterns, metadata keys, entity contexts | |
| 6 | `tool_defs.py` — OpenRouter function-calling JSON definitions | |
| 7 | `executor.py` — dispatches tool calls to facade | |
| 8 | Unit tests for local fallback | |
| 9 | Integration tests for hosted Supermemory | |
| 10 | Wire into orchestrator (coordinate with teammate) | |
