# Web Search + Rerank Guide

The `/v1/search/rerank` endpoint searches the web via Brave Search, then reranks results using the BGE reranker model (`BAAI/bge-reranker-v2-m3`) to produce relevance-scored results.

## How it works

1. **Search** — Sends the query to the Brave Web Search API
2. **Rerank** — Passes `[query, "title. snippet"]` pairs through the BGE cross-encoder
3. **Score** — Applies sigmoid normalization to produce scores in `[0, 1]`
4. **Sort** — Returns results ordered by descending relevance score

## API reference

### `POST /v1/search/rerank`

**Request body:**

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `query` | string | *(required)* | Search query |
| `num_results` | int (1-20) | 10 | Number of results |
| `provider` | string | `"brave"` | Search provider |

**Response body:**

| Field | Type | Description |
|-------|------|-------------|
| `query` | string | Echo of the input query |
| `provider` | string | Provider used |
| `results` | array | Reranked results (see below) |
| `num_raw` | int | Raw results from search API |
| `num_reranked` | int | Results after reranking |

Each result object:

| Field | Type | Description |
|-------|------|-------------|
| `title` | string | Page title |
| `url` | string | Page URL |
| `snippet` | string | Text snippet |
| `score` | float (0-1) | Relevance score |

### Examples

**curl:**

```bash
curl -X POST https://<your-modal-url>/v1/search/rerank \
  -H "Authorization: Bearer $BIND_TOOLS_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"query": "EGFR inhibitor mechanism", "num_results": 5}'
```

**Python:**

```python
import httpx

resp = httpx.post(
    "https://<your-modal-url>/v1/search/rerank",
    headers={"Authorization": f"Bearer {api_key}"},
    json={"query": "EGFR inhibitor mechanism", "num_results": 5},
)
data = resp.json()
for r in data["results"]:
    print(f"{r['score']:.4f}  {r['title']}")
```

## CLI usage

Install the package, then use `bind-search`:

```bash
pip install -e .
```

### Basic search

```bash
bind-search "EGFR inhibitor mechanism"
```

### With options

```bash
# More results, show snippets
bind-search "kinase selectivity" --num-results 15 --verbose

# JSON output for piping
bind-search "p53 drug target" --json-out | jq '.results[0]'

# Quiet mode (no spinner)
bind-search "CDK4/6 inhibitor" --quiet
```

### Environment variables

| Variable | Description |
|----------|-------------|
| `BIND_TOOLS_API_KEY` | **(required)** API key for authentication |
| `BIND_TOOLS_BASE_URL` | Override the default Modal deployment URL |

## Setup

### 1. Create the Brave API key secret in Modal

```bash
modal secret create search-api-keys BRAVE_API_KEY=<your-brave-key>
```

### 2. Deploy

```bash
modal deploy src/bind_tools/modal_app/app.py
```

### 3. Verify

```bash
# Health check
curl https://<your-modal-url>/v1/health

# Test search
export BIND_TOOLS_API_KEY=<your-key>
bind-search "EGFR inhibitor" --verbose
```
