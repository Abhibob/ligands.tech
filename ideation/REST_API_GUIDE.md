# Bind-Tools REST API Guide

HTTP REST endpoints for running **Boltz-2** (structure prediction) and **GNINA** (molecular docking) on Modal cloud GPUs.

## Base URL

```
https://benwu408--bind-tools-gpu-webapi-serve.modal.run
```

## Authentication

All POST endpoints require a Bearer token in the `Authorization` header:

```
Authorization: Bearer <your-api-key>
```

The API key is the value of `BIND_TOOLS_API_KEY` set in the `bind-tools-api-key` Modal secret.

## File Encoding

Input and output files are transferred as base64-encoded JSON objects:

```json
{
  "name": "protein.pdb",
  "data": "<base64-encoded file contents>"
}
```

---

## Endpoints

| Method | Path                 | Auth     | Description            |
|--------|----------------------|----------|------------------------|
| GET    | `/v1/health`         | No       | Health check           |
| POST   | `/v1/boltz/predict`  | Required | Structure prediction   |
| POST   | `/v1/gnina/dock`     | Required | Molecular docking      |
| POST   | `/v1/gnina/score`    | Required | Pose scoring           |
| POST   | `/v1/gnina/minimize` | Required | Pose minimization      |
| GET    | `/docs`              | No       | Interactive Swagger UI |

---

## Health Check

```bash
curl https://benwu408--bind-tools-gpu-webapi-serve.modal.run/v1/health
# {"status":"ok"}
```

---

## Boltz-2 Structure Prediction

**`POST /v1/boltz/predict`**

Predicts protein-ligand complex structures using Boltz-2 on an A100 GPU.

### Request Body

| Field              | Type            | Required | Description                                              |
|--------------------|-----------------|----------|----------------------------------------------------------|
| `upstream_yaml`    | object          | Yes      | Boltz input YAML as a JSON dict (see examples below)     |
| `input_files`      | list of FileB64 | No       | Referenced files (FASTA, SDF, PDB) when using file paths |
| `accelerator`      | string          | No       | `"gpu"` (default) or `"cpu"`                             |
| `use_msa_server`   | boolean         | No       | Use MSA server (default `false`)                         |
| `recycling_steps`  | integer         | No       | Number of recycling steps                                |
| `diffusion_samples`| integer         | No       | Number of diffusion samples (default varies)             |
| `seed`             | integer         | No       | Random seed for reproducibility                          |

### Response Body

| Field                 | Type            | Description                                    |
|-----------------------|-----------------|------------------------------------------------|
| `returncode`          | integer         | Process exit code (0 = success)                |
| `stdout`              | string          | Process stdout (last 5000 chars)               |
| `stderr`              | string          | Process stderr (last 5000 chars)               |
| `output_files`        | list of FileB64 | Output files (structures, confidence, affinity)|
| `confidence`          | object or null  | Parsed confidence scores                       |
| `affinity`            | object or null  | Parsed affinity predictions                    |
| `primary_complex_path`| string or null  | Filename of the primary predicted structure    |
| `structure_filenames` | list of string  | All predicted structure filenames              |

### Example: Predict with Inline Sequence + SMILES

The simplest case — provide protein sequence and ligand SMILES directly in the YAML:

```bash
curl -X POST https://benwu408--bind-tools-gpu-webapi-serve.modal.run/v1/boltz/predict \
  -H "Authorization: Bearer $BIND_TOOLS_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "upstream_yaml": {
      "sequences": [
        {"protein": {"id": "A", "sequence": "MKTAYIAKQRQISFVKSHFSRQLE"}},
        {"ligand": {"id": "B", "smiles": "CC(=O)Oc1ccccc1C(=O)O"}}
      ]
    },
    "diffusion_samples": 1
  }'
```

### Example: Predict with Input Files

When your ligand is in an SDF file, base64-encode it and reference it in the YAML:

```bash
LIGAND_B64=$(base64 < ligand.sdf)

curl -X POST https://benwu408--bind-tools-gpu-webapi-serve.modal.run/v1/boltz/predict \
  -H "Authorization: Bearer $BIND_TOOLS_API_KEY" \
  -H "Content-Type: application/json" \
  -d "{
    \"upstream_yaml\": {
      \"sequences\": [
        {\"protein\": {\"id\": \"A\", \"sequence\": \"MKTAYIAKQRQISFVKSHFSRQLE\"}},
        {\"ligand\": {\"id\": \"B\", \"sdf\": \"ligand.sdf\"}}
      ]
    },
    \"input_files\": [
      {\"name\": \"ligand.sdf\", \"data\": \"$LIGAND_B64\"}
    ],
    \"diffusion_samples\": 1
  }"
```

### Python Example

```python
import base64
import requests

API_KEY = "your-api-key"
BASE = "https://benwu408--bind-tools-gpu-webapi-serve.modal.run"

# Predict a protein-ligand complex
resp = requests.post(
    f"{BASE}/v1/boltz/predict",
    headers={"Authorization": f"Bearer {API_KEY}"},
    json={
        "upstream_yaml": {
            "sequences": [
                {"protein": {"id": "A", "sequence": "MKTAYIAKQRQISFVKSHFSRQLE"}},
                {"ligand": {"id": "B", "smiles": "CC(=O)Oc1ccccc1C(=O)O"}},
            ]
        },
        "diffusion_samples": 1,
    },
)
resp.raise_for_status()
result = resp.json()

print(f"Return code: {result['returncode']}")
print(f"Confidence: {result['confidence']}")
print(f"Affinity: {result['affinity']}")
print(f"Structure files: {result['structure_filenames']}")

# Save output files to disk
for f in result["output_files"]:
    with open(f["name"], "wb") as fh:
        fh.write(base64.b64decode(f["data"]))
    print(f"Saved {f['name']}")
```

---

## GNINA Molecular Docking

**`POST /v1/gnina/dock`**

Docks a ligand into a protein binding site using GNINA on a T4 GPU.

### Request Body (shared by dock, score, minimize)

| Field             | Type            | Required | Description                                          |
|-------------------|-----------------|----------|------------------------------------------------------|
| `gnina_args`      | list of string  | Yes      | GNINA CLI args using filenames (not full paths)      |
| `input_files`     | list of FileB64 | Yes      | All input files referenced in `gnina_args`           |
| `output_filename` | string or null  | No       | Expected output SDF filename (`null` for score mode) |

### Response Body

| Field         | Type           | Description                                |
|---------------|----------------|--------------------------------------------|
| `returncode`  | integer        | Process exit code (0 = success)            |
| `stdout`      | string         | GNINA stdout (scores, poses)               |
| `stderr`      | string         | GNINA stderr                               |
| `output_file` | FileB64 or null| Output SDF if produced, otherwise null     |

### GNINA Args Reference

The `gnina_args` list mirrors the GNINA command line. Common flags:

| Flag                | Description                         |
|---------------------|-------------------------------------|
| `-r <file>`         | Receptor file (PDB/PDBQT)          |
| `-l <file>`         | Ligand file (SDF/MOL2/PDBQT)       |
| `--autobox_ligand <file>` | Define box from a reference ligand |
| `-o <file>`         | Output file for docked poses        |
| `--exhaustiveness N`| Search thoroughness (default 8)     |
| `--num_modes N`     | Max number of poses to return       |
| `--score_only`      | Score without docking (score mode)  |
| `--minimize`        | Minimize poses (minimize mode)      |

### Example: Dock a Ligand (curl)

```bash
RECEPTOR_B64=$(base64 < protein.pdb)
LIGAND_B64=$(base64 < ligand.sdf)
AUTOBOX_B64=$(base64 < reference.sdf)

curl -X POST https://benwu408--bind-tools-gpu-webapi-serve.modal.run/v1/gnina/dock \
  -H "Authorization: Bearer $BIND_TOOLS_API_KEY" \
  -H "Content-Type: application/json" \
  -d "{
    \"gnina_args\": [
      \"-r\", \"protein.pdb\",
      \"-l\", \"ligand.sdf\",
      \"--autobox_ligand\", \"reference.sdf\",
      \"-o\", \"docked.sdf\",
      \"--exhaustiveness\", \"16\"
    ],
    \"input_files\": [
      {\"name\": \"protein.pdb\", \"data\": \"$RECEPTOR_B64\"},
      {\"name\": \"ligand.sdf\", \"data\": \"$LIGAND_B64\"},
      {\"name\": \"reference.sdf\", \"data\": \"$AUTOBOX_B64\"}
    ],
    \"output_filename\": \"docked.sdf\"
  }"
```

### Example: Dock a Ligand (Python)

```python
import base64
import requests

API_KEY = "your-api-key"
BASE = "https://benwu408--bind-tools-gpu-webapi-serve.modal.run"

# Read and encode input files
receptor_b64 = base64.b64encode(open("protein.pdb", "rb").read()).decode()
ligand_b64 = base64.b64encode(open("ligand.sdf", "rb").read()).decode()
autobox_b64 = base64.b64encode(open("reference.sdf", "rb").read()).decode()

resp = requests.post(
    f"{BASE}/v1/gnina/dock",
    headers={"Authorization": f"Bearer {API_KEY}"},
    json={
        "gnina_args": [
            "-r", "protein.pdb",
            "-l", "ligand.sdf",
            "--autobox_ligand", "reference.sdf",
            "-o", "docked.sdf",
            "--exhaustiveness", "16",
        ],
        "input_files": [
            {"name": "protein.pdb", "data": receptor_b64},
            {"name": "ligand.sdf", "data": ligand_b64},
            {"name": "reference.sdf", "data": autobox_b64},
        ],
        "output_filename": "docked.sdf",
    },
)
resp.raise_for_status()
result = resp.json()

print(f"Return code: {result['returncode']}")
print(f"GNINA output:\n{result['stdout']}")

# Save docked poses
if result["output_file"]:
    with open(result["output_file"]["name"], "wb") as fh:
        fh.write(base64.b64decode(result["output_file"]["data"]))
    print(f"Saved {result['output_file']['name']}")
```

---

## GNINA Pose Scoring

**`POST /v1/gnina/score`**

Scores existing ligand poses against a receptor without docking.

```python
resp = requests.post(
    f"{BASE}/v1/gnina/score",
    headers={"Authorization": f"Bearer {API_KEY}"},
    json={
        "gnina_args": [
            "-r", "protein.pdb",
            "-l", "poses.sdf",
            "--score_only",
        ],
        "input_files": [
            {"name": "protein.pdb", "data": receptor_b64},
            {"name": "poses.sdf", "data": poses_b64},
        ],
        # No output_filename for score mode
    },
)
result = resp.json()
print(result["stdout"])  # Scores are printed to stdout
```

---

## GNINA Pose Minimization

**`POST /v1/gnina/minimize`**

Minimizes existing poses (local energy optimization) and returns the refined SDF.

```python
resp = requests.post(
    f"{BASE}/v1/gnina/minimize",
    headers={"Authorization": f"Bearer {API_KEY}"},
    json={
        "gnina_args": [
            "-r", "protein.pdb",
            "-l", "poses.sdf",
            "--autobox_ligand", "reference.sdf",
            "--minimize",
            "-o", "minimized.sdf",
        ],
        "input_files": [
            {"name": "protein.pdb", "data": receptor_b64},
            {"name": "poses.sdf", "data": poses_b64},
            {"name": "reference.sdf", "data": autobox_b64},
        ],
        "output_filename": "minimized.sdf",
    },
)
result = resp.json()

if result["output_file"]:
    with open("minimized.sdf", "wb") as fh:
        fh.write(base64.b64decode(result["output_file"]["data"]))
```

---

## Error Handling

All endpoints return standard HTTP status codes:

| Code | Meaning                                              |
|------|------------------------------------------------------|
| 200  | Success                                              |
| 401  | Missing or invalid API key                           |
| 422  | Validation error (malformed request body)            |
| 500  | Internal server error (check `stderr` in response)   |

A `returncode` of `0` in the response body means the underlying tool (Boltz/GNINA) succeeded. A non-zero `returncode` with HTTP 200 means the request was processed but the tool itself reported an error — check `stdout` and `stderr` for details.

## Interactive API Docs

Visit the Swagger UI for interactive testing and full schema documentation:

```
https://benwu408--bind-tools-gpu-webapi-serve.modal.run/docs
```
