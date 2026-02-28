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
