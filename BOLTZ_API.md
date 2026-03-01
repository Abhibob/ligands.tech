# Boltz-2 Structure Prediction API

Predict protein and protein-ligand complex 3D structures using [Boltz-2](https://github.com/jwohlwend/boltz) on an NVIDIA A100 GPU via Modal.

## Base URL

```
https://benwu408--bind-tools-gpu-webapi-serve.modal.run
```

## Authentication

All POST endpoints require a Bearer token:

```
Authorization: Bearer <BIND_TOOLS_API_KEY>
```

The key is stored in the `bind-tools-api-key` Modal secret and locally in `.env`.

---

## Quick Start

### Protein + Ligand (curl)

```bash
curl -X POST https://benwu408--bind-tools-gpu-webapi-serve.modal.run/v1/boltz/predict \
  -H "Authorization: Bearer $BIND_TOOLS_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "upstream_yaml": {
      "version": 1,
      "sequences": [
        {"protein": {"id": "A", "sequence": "FVNQHLCGSHLVEALYLVCGERGFFYTPKT"}},
        {"ligand": {"id": "B", "smiles": "CC(=O)OC1=CC=CC=C1C(=O)O"}}
      ]
    },
    "use_msa_server": true,
    "diffusion_samples": 1
  }'
```

### Protein Only (curl)

```bash
curl -X POST https://benwu408--bind-tools-gpu-webapi-serve.modal.run/v1/boltz/predict \
  -H "Authorization: Bearer $BIND_TOOLS_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "upstream_yaml": {
      "version": 1,
      "sequences": [
        {"protein": {"id": "A", "sequence": "FVNQHLCGSHLVEALYLVCGERGFFYTPKT"}}
      ]
    },
    "use_msa_server": true,
    "diffusion_samples": 1
  }'
```

### With Affinity Prediction (curl)

Add a `properties` block to the YAML to get binding affinity scores:

```bash
curl -X POST https://benwu408--bind-tools-gpu-webapi-serve.modal.run/v1/boltz/predict \
  -H "Authorization: Bearer $BIND_TOOLS_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "upstream_yaml": {
      "version": 1,
      "sequences": [
        {"protein": {"id": "A", "sequence": "IVGGYTCGANTVPYQVSLNSGYHFCGGSLINSQWVVSAAHCYKSGIQVRLGEDNINVVEGNEQFISASKSIVHPSYNSNTLNNDIMLIKLKSAASLNSRVASISLPTSCASAGTQCLISGWGNTKSSGTSYPDVLKCLKAPILSDSSCKSAYPGQITSNMFCAGYLEGGKDSCQGDSGGPVVCSGKLQGIVSWGSGCAQKNKPGVYTKVCNYVSWIKQTIASN"}},
        {"ligand": {"id": "B", "smiles": "C1=CC=C(C=C1)C(=N)N"}}
      ],
      "properties": [{"affinity": {"binder": "B"}}]
    },
    "use_msa_server": true,
    "diffusion_samples": 1
  }'
```

### Python

```python
import base64
import requests

API_KEY = "your-api-key"
BASE = "https://benwu408--bind-tools-gpu-webapi-serve.modal.run"

resp = requests.post(
    f"{BASE}/v1/boltz/predict",
    headers={"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"},
    json={
        "upstream_yaml": {
            "version": 1,
            "sequences": [
                {"protein": {"id": "A", "sequence": "FVNQHLCGSHLVEALYLVCGERGFFYTPKT"}},
                {"ligand": {"id": "B", "smiles": "CC(=O)OC1=CC=CC=C1C(=O)O"}},
            ],
        },
        "use_msa_server": True,
        "diffusion_samples": 1,
    },
    timeout=600,
)
resp.raise_for_status()
result = resp.json()

print(f"Return code: {result['returncode']}")
print(f"Confidence:  {result['confidence']}")
print(f"Affinity:    {result['affinity']}")
print(f"Structures:  {result['structure_filenames']}")

# Save output files (PDB structures, confidence/affinity JSONs)
for f in result["output_files"]:
    with open(f["name"], "wb") as fh:
        fh.write(base64.b64decode(f["data"]))
    print(f"Saved {f['name']}")
```

---

## Endpoint Reference

```
POST /v1/boltz/predict
```

### Request Body

| Field | Type | Required | Default | Description |
|---|---|---|---|---|
| `upstream_yaml` | object | **Yes** | — | Boltz input YAML as a JSON dict (see [YAML Format](#upstream-yaml-format)) |
| `input_files` | list of [FileB64](#fileb64-format) | No | `[]` | Referenced files (FASTA, SDF, PDB, MOL2) as base64 |
| `accelerator` | string | No | `"gpu"` | `"gpu"` or `"cpu"` |
| `use_msa_server` | boolean | No | `false` | Use remote MSA server for multiple sequence alignment |
| `recycling_steps` | integer | No | `null` | Number of recycling steps (0+) |
| `diffusion_samples` | integer | No | `null` | Number of structure samples to generate (1+) |
| `seed` | integer | No | `null` | Random seed for reproducibility |

### Response Body

| Field | Type | Description |
|---|---|---|
| `returncode` | integer | Process exit code (`0` = success) |
| `stdout` | string | Process stdout (last 5000 chars) |
| `stderr` | string | Process stderr (last 5000 chars) |
| `output_files` | list of [FileB64](#fileb64-format) | Output structures, confidence JSON, affinity JSON — all base64-encoded |
| `confidence` | object or `null` | Parsed confidence metrics (see [Confidence Scores](#confidence-scores)) |
| `affinity` | object or `null` | Parsed affinity predictions (see [Affinity Scores](#affinity-scores)) |
| `primary_complex_path` | string or `null` | Filename of the best predicted structure (e.g. `"complex_model_0.pdb"`) |
| `structure_filenames` | list of string | All predicted structure filenames |

### FileB64 Format

Used for both input and output files:

```json
{"name": "protein.pdb", "data": "<base64-encoded contents>"}
```

---

## Upstream YAML Format

The `upstream_yaml` field is a JSON representation of the YAML that Boltz-2 expects. It always has `version: 1`.

### Minimal Structure

```json
{
  "version": 1,
  "sequences": [
    {"protein": {"id": "A", "sequence": "MKTAYIAKQRQISFVKSHFSRQLE"}},
    {"ligand": {"id": "B", "smiles": "CC(=O)Oc1ccccc1C(=O)O"}}
  ]
}
```

### Full Structure (all optional fields)

```json
{
  "version": 1,
  "sequences": [
    {"protein": {"id": "A", "sequence": "MKTAYIAKQRQISFVKSHFSRQLE"}},
    {"ligand": {"id": "B", "smiles": "CC(=O)Oc1ccccc1C(=O)O"}}
  ],
  "constraints": {
    "pocket_residues": ["A:745", "A:793"],
    "contacts": ["B:1@N=A:50@O"],
    "method_conditioning": ["cryo-em"]
  },
  "properties": [
    {"affinity": {"binder": "B"}}
  ]
}
```

### Sequence Entity Types

#### Protein

Provide a protein sequence inline or via a FASTA file path:

```json
{"protein": {"id": "A", "sequence": "MKTAYIAKQRQISFVKSHFSRQLE"}}
```

Or with a file reference (must be included in `input_files`):

```json
{"protein": {"id": "A", "fasta": "protein.fasta"}}
```

Supported keys: `sequence`, `fasta`, `pdb`, `cif`. If using `pdb` or `cif`, you must also provide `sequence` or `fasta`.

#### Ligand

Provide a ligand as SMILES or a file:

```json
{"ligand": {"id": "B", "smiles": "CC(=O)Oc1ccccc1C(=O)O"}}
```

Or with a file reference:

```json
{"ligand": {"id": "B", "sdf": "ligand.sdf"}}
```

Supported keys: `smiles`, `sdf`, `mol2`. Exactly one is required per ligand.

### Constraints (optional)

| Key | Format | Description |
|---|---|---|
| `pocket_residues` | `["A:745", "A:793"]` | Residues to guide docking (`chain:resid`) |
| `contacts` | `["B:1@N=A:50@O"]` | Enforce specific ligand-protein atom contacts |
| `method_conditioning` | `["cryo-em"]` | Bias toward experimental method (cryo-em, nmr, x-ray) |

### Properties (optional)

Add this block to enable affinity prediction:

```json
"properties": [{"affinity": {"binder": "B"}}]
```

`binder` must be the `id` of a ligand in the `sequences` list.

---

## Response Details

### Confidence Scores

When a prediction succeeds, `confidence` contains:

| Key | Type | Description |
|---|---|---|
| `confidence` | float | Overall confidence score |
| `ptm` | float | Predicted TM-score (0–1, higher = better fold) |
| `iptm` | float | Interface TM-score (0–1, higher = better complex) |
| `complex_plddt` | float | pLDDT for the complex |
| `complex_iplddt` | float | Interface pLDDT |
| `pair_chains_iptm` | float | Pairwise chain interface score |
| `ranking_score` | float | Internal ranking metric |

### Affinity Scores

Only present when `properties.affinity` is set in the YAML:

| Key | Type | Description |
|---|---|---|
| `affinity_probability_binary` | float | P(binder) in [0, 1] — probability the ligand binds |
| `affinity_pred_value` | float | Predicted binding affinity value |

### Output Files

The `output_files` list contains base64-encoded files:

| File Pattern | Description |
|---|---|
| `*_model_0.pdb` | Primary predicted structure (PDB format) |
| `*_model_N.pdb` | Additional sampled structures (when `diffusion_samples` > 1) |
| `confidence_*_model_0.json` | Raw confidence metrics JSON |
| `affinity_*.json` | Raw affinity prediction JSON (when affinity is enabled) |

---

## Using Input Files

When your protein or ligand is in a file rather than inline, base64-encode the file and include it in `input_files`. Reference the filename in the YAML.

### Ligand from SDF File (curl)

```bash
LIGAND_B64=$(base64 < ligand.sdf)

curl -X POST https://benwu408--bind-tools-gpu-webapi-serve.modal.run/v1/boltz/predict \
  -H "Authorization: Bearer $BIND_TOOLS_API_KEY" \
  -H "Content-Type: application/json" \
  -d "{
    \"upstream_yaml\": {
      \"version\": 1,
      \"sequences\": [
        {\"protein\": {\"id\": \"A\", \"sequence\": \"MKTAYIAKQRQISFVKSHFSRQLE\"}},
        {\"ligand\": {\"id\": \"B\", \"sdf\": \"ligand.sdf\"}}
      ]
    },
    \"input_files\": [
      {\"name\": \"ligand.sdf\", \"data\": \"$LIGAND_B64\"}
    ],
    \"use_msa_server\": true,
    \"diffusion_samples\": 1
  }"
```

### Protein from FASTA + Ligand from SDF (Python)

```python
import base64
import requests

API_KEY = "your-api-key"
BASE = "https://benwu408--bind-tools-gpu-webapi-serve.modal.run"

fasta_b64 = base64.b64encode(open("protein.fasta", "rb").read()).decode()
sdf_b64 = base64.b64encode(open("ligand.sdf", "rb").read()).decode()

resp = requests.post(
    f"{BASE}/v1/boltz/predict",
    headers={"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"},
    json={
        "upstream_yaml": {
            "version": 1,
            "sequences": [
                {"protein": {"id": "A", "fasta": "protein.fasta"}},
                {"ligand": {"id": "B", "sdf": "ligand.sdf"}},
            ],
        },
        "input_files": [
            {"name": "protein.fasta", "data": fasta_b64},
            {"name": "ligand.sdf", "data": sdf_b64},
        ],
        "use_msa_server": True,
        "diffusion_samples": 1,
    },
    timeout=600,
)
```

---

## Infrastructure

| Property | Value |
|---|---|
| GPU | NVIDIA A100 (40 GB VRAM) |
| Container timeout | 30 minutes |
| Subprocess timeout | 25 minutes |
| Model weights | ~3.6 GB, cached in a Modal Volume after first run |
| Cold start | ~30–60 seconds (weights already cached) |
| Concurrency | Up to 10 concurrent requests per container |
| Cost | ~$3.70/hr (A100 on Modal) |

## Timeouts

Set your HTTP client timeout to **at least 600 seconds** (10 minutes). A typical prediction takes 1–5 minutes depending on protein size, but cold starts and MSA computation can add time.

```python
resp = requests.post(url, json=payload, headers=headers, timeout=600)
```

```bash
curl --max-time 600 ...
```

---

## Error Handling

### HTTP Status Codes

| Code | Meaning |
|---|---|
| 200 | Request processed (check `returncode` for tool-level success) |
| 401 | Missing or invalid API key |
| 422 | Validation error (malformed request body) |
| 500 | Internal server error |

### Interpreting `returncode`

A `200` HTTP response with `returncode: 0` means full success. A `200` with non-zero `returncode` means the request reached Boltz but it failed — check `stdout` and `stderr` for details.

Common failure causes:
- **Missing MSA**: `use_msa_server` not set and no pre-computed MSA provided
- **Invalid SMILES**: Malformed ligand SMILES string
- **GPU OOM**: Protein too large for A100 memory (try reducing `diffusion_samples`)

---

## Test Sequences

These sequences are used in the integration test suite (`tests/test_boltz_api.py`) and are known to work:

```python
# Insulin B-chain (30 residues) — fast, good for smoke tests
INSULIN_B_CHAIN = "FVNQHLCGSHLVEALYLVCGERGFFYTPKT"

# Bovine trypsin (223 residues) — well-studied serine protease
TRYPSIN_SEQUENCE = (
    "IVGGYTCGANTVPYQVSLNSGYHFCGGSLINSQWVVSAAHCYKSGIQVRLGEDNINVVEG"
    "NEQFISASKSIVHPSYNSNTLNNDIMLIKLKSAASLNSRVASISLPTSCASAGTQCLISG"
    "WGNTKSSGTSYPDVLKCLKAPILSDSSCKSAYPGQITSNMFCAGYLEGGKDSCQGDSGG"
    "PVVCSGKLQGIVSWGSGCAQKNKPGVYTKVCNYVSWIKQTIASN"
)

# Benzamidine — classic trypsin inhibitor
BENZAMIDINE_SMILES = "C1=CC=C(C=C1)C(=N)N"

# Aspirin
ASPIRIN_SMILES = "CC(=O)OC1=CC=CC=C1C(=O)O"
```

---

## Running Integration Tests

```bash
# Fast tests only (health + auth, no GPU)
pytest tests/test_boltz_api.py -v -s -m "not slow"

# All tests including GPU predictions (~10 min)
pytest tests/test_boltz_api.py -v -s

# GPU tests only
pytest tests/test_boltz_api.py -v -s -m slow
```

---

## Interactive Docs

Swagger UI with try-it-out:

```
https://benwu408--bind-tools-gpu-webapi-serve.modal.run/docs
```