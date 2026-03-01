# Modal GPU Cloud Deployment

Run Boltz-2 (structure prediction) and GNINA (molecular docking) on Modal cloud GPUs instead of requiring local CUDA/Docker setup.

## Prerequisites

1. Install the Modal SDK:
   ```bash
   pip install "bind-tools[modal]"
   # or standalone:
   pip install modal python-dotenv
   ```

2. Authenticate with Modal:

   **Option A — Interactive (local machine with browser):**
   ```bash
   modal token new
   ```

   **Option B — Headless server / CI / Docker:**

   Generate an API token at [modal.com/settings](https://modal.com/settings) under **API Tokens**, then set the credentials via a `.env` file or environment variables:

   ```bash
   # .env (project root — already in .gitignore)
   MODAL_TOKEN_ID=ak-xxxxxxxxxxxxxxxx
   MODAL_TOKEN_SECRET=as-xxxxxxxxxxxxxxxx
   ```

   Or export them directly:
   ```bash
   export MODAL_TOKEN_ID=ak-xxxxxxxxxxxxxxxx
   export MODAL_TOKEN_SECRET=as-xxxxxxxxxxxxxxxx
   ```

   The Modal SDK picks these up automatically. The `.env` file is loaded via `python-dotenv` at startup when using `--modal`.

## Usage

Add `--modal` to any bind-boltz or bind-gnina command to run on cloud GPUs.

### Boltz-2 Structure Prediction

```bash
# Predict structure on a Modal A100 GPU
bind-boltz predict --modal \
  --protein-fasta protein.fasta \
  --ligand-smiles "CC(=O)Oc1ccccc1C(=O)O" \
  --json-out result.json

# With affinity estimation
bind-boltz predict --modal \
  --protein-sequence "MKWVTFISLLLLFSSAYSRGV..." \
  --ligand-smiles "C1=CC=CC=C1" \
  --task both \
  --json-out result.json
```

### GNINA Molecular Docking

```bash
# Dock on a Modal T4 GPU
bind-gnina dock --modal \
  --receptor protein.pdb \
  --ligand ligand.sdf \
  --autobox-ligand reference.sdf \
  --json-out dock_result.json

# Score existing poses
bind-gnina score --modal \
  --receptor protein.pdb \
  --ligand poses.sdf

# Minimize poses
bind-gnina minimize --modal \
  --receptor protein.pdb \
  --ligand poses.sdf \
  --autobox-ligand reference.sdf \
  --json-out min_result.json
```

## Environment Variable

Set `BIND_TOOLS_USE_MODAL=1` to default all runs to Modal without passing `--modal`:

```bash
export BIND_TOOLS_USE_MODAL=1
bind-boltz predict --protein-fasta protein.fasta --ligand-smiles "CCO"
```

The `--modal` flag always takes precedence when explicitly provided.

## GPU Selection

| Tool   | GPU  | VRAM  | Why                                         |
|--------|------|-------|---------------------------------------------|
| Boltz-2| A100 | 40 GB | Diffusion model requires significant VRAM   |
| GNINA  | T4   | 16 GB | CNN scoring is lightweight; most cost-effective |

## Cost Considerations

- **A100** (Boltz-2): ~$3.70/hr on Modal. A typical prediction takes 2-10 minutes.
- **T4** (GNINA): ~$0.60/hr on Modal. A typical docking takes 1-5 minutes.
- Containers scale to zero when idle -- you only pay for active compute time.

## First Run / Cold Starts

On the **first run**, expect additional setup time:

- **Boltz-2**: The model weights (~3.6 GB) are downloaded and cached in a Modal Volume (`bind-tools-boltz-weights`). First run may take ~5 minutes for the download; subsequent runs reuse the cached weights.
- **GNINA**: The Docker image is pulled from `gnina/gnina:latest`. First run may take 1-2 minutes for image setup.

After the first run, Modal caches the container images. If a container has been idle for ~15 minutes it will shut down and the next request will incur a ~30-60 second cold start.

## REST API

In addition to the SDK-based (`--modal`) access, the deployed app exposes HTTP REST endpoints so any client with an API key can call Boltz and GNINA via simple HTTP requests.

### Setup — Create the API Key Secret (one-time)

```bash
modal secret create bind-tools-api-key BIND_TOOLS_API_KEY=$(openssl rand -hex 32)
```

Then deploy (or redeploy) the app:
```bash
modal deploy src/bind_tools/modal_app/app.py
```

### Base URL

```
https://benwu408--bind-tools-gpu-webapi-serve.modal.run
```

### Endpoints

| Method | Path                    | Description              |
|--------|-------------------------|--------------------------|
| GET    | `/v1/health`            | Health check (no auth)   |
| POST   | `/v1/boltz/predict`     | Structure prediction     |
| POST   | `/v1/gnina/dock`        | Molecular docking        |
| POST   | `/v1/gnina/score`       | Pose scoring             |
| POST   | `/v1/gnina/minimize`    | Pose minimization        |
| GET    | `/docs`                 | Swagger UI               |

All POST endpoints require `Authorization: Bearer <API_KEY>`.

Files are sent as base64-encoded JSON objects: `{"name": "protein.pdb", "data": "<base64>"}`.

### Examples

#### Health Check

```bash
curl https://benwu408--bind-tools-gpu-webapi-serve.modal.run/v1/health
```

#### Boltz Structure Prediction (curl)

```bash
curl -X POST https://benwu408--bind-tools-gpu-webapi-serve.modal.run/v1/boltz/predict \
  -H "Authorization: Bearer $BIND_TOOLS_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "upstream_yaml": {
      "sequences": [
        {"protein": {"id": "A", "sequence": "MKWVTFISLLLLFSSAYSRGV..."}},
        {"ligand": {"id": "B", "smiles": "CC(=O)Oc1ccccc1C(=O)O"}}
      ]
    },
    "diffusion_samples": 1
  }'
```

#### Boltz Structure Prediction (Python)

```python
import base64, requests

API_KEY = "your-api-key"
BASE = "https://benwu408--bind-tools-gpu-webapi-serve.modal.run"

resp = requests.post(
    f"{BASE}/v1/boltz/predict",
    headers={"Authorization": f"Bearer {API_KEY}"},
    json={
        "upstream_yaml": {
            "sequences": [
                {"protein": {"id": "A", "sequence": "MKWVTFISLLLLFSSAYSRGV..."}},
                {"ligand": {"id": "B", "smiles": "CC(=O)Oc1ccccc1C(=O)O"}},
            ]
        },
        "diffusion_samples": 1,
    },
)
result = resp.json()

# Decode output structure file
for f in result["output_files"]:
    with open(f["name"], "wb") as fh:
        fh.write(base64.b64decode(f["data"]))
```

#### GNINA Docking (curl)

```bash
RECEPTOR_B64=$(base64 < protein.pdb)
LIGAND_B64=$(base64 < ligand.sdf)
AUTOBOX_B64=$(base64 < reference.sdf)

curl -X POST https://benwu408--bind-tools-gpu-webapi-serve.modal.run/v1/gnina/dock \
  -H "Authorization: Bearer $BIND_TOOLS_API_KEY" \
  -H "Content-Type: application/json" \
  -d "{
    \"gnina_args\": [\"-r\", \"protein.pdb\", \"-l\", \"ligand.sdf\", \"--autobox_ligand\", \"reference.sdf\", \"-o\", \"output.sdf\"],
    \"input_files\": [
      {\"name\": \"protein.pdb\", \"data\": \"$RECEPTOR_B64\"},
      {\"name\": \"ligand.sdf\", \"data\": \"$LIGAND_B64\"},
      {\"name\": \"reference.sdf\", \"data\": \"$AUTOBOX_B64\"}
    ],
    \"output_filename\": \"output.sdf\"
  }"
```

#### GNINA Docking (Python)

```python
import base64, requests

API_KEY = "your-api-key"
BASE = "https://benwu408--bind-tools-gpu-webapi-serve.modal.run"

receptor_b64 = base64.b64encode(open("protein.pdb", "rb").read()).decode()
ligand_b64 = base64.b64encode(open("ligand.sdf", "rb").read()).decode()
autobox_b64 = base64.b64encode(open("reference.sdf", "rb").read()).decode()

resp = requests.post(
    f"{BASE}/v1/gnina/dock",
    headers={"Authorization": f"Bearer {API_KEY}"},
    json={
        "gnina_args": ["-r", "protein.pdb", "-l", "ligand.sdf",
                       "--autobox_ligand", "reference.sdf", "-o", "output.sdf"],
        "input_files": [
            {"name": "protein.pdb", "data": receptor_b64},
            {"name": "ligand.sdf", "data": ligand_b64},
            {"name": "reference.sdf", "data": autobox_b64},
        ],
        "output_filename": "output.sdf",
    },
)
result = resp.json()

# Save docked poses
if result["output_file"]:
    with open(result["output_file"]["name"], "wb") as fh:
        fh.write(base64.b64decode(result["output_file"]["data"]))
```

## Troubleshooting

### "modal: command not found" or ImportError
```bash
pip install "modal>=0.73.0"
```

### "Modal credentials not found"
Either run `modal token new` (interactive) or set credentials in `.env`:
```bash
# .env
MODAL_TOKEN_ID=ak-xxxxxxxxxxxxxxxx
MODAL_TOKEN_SECRET=as-xxxxxxxxxxxxxxxx
```

### Timeout errors
Boltz-2 predictions with large proteins or many diffusion samples can take a long time. The default timeout is 30 minutes. For very large jobs, consider reducing `--diffusion-samples` or splitting into smaller targets.

### "No GPU available" on Modal
Modal auto-provisions GPUs. If you see availability errors, the GPU type may be temporarily exhausted in your region. Try again after a few minutes.

### Checking Modal dashboard
Visit https://modal.com/apps to monitor running containers, view logs, and check billing.
