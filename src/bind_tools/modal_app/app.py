"""Shared Modal app definition, volume, and constants."""

from __future__ import annotations

from bind_tools.modal_app import ensure_modal_auth

ensure_modal_auth()

import modal

app = modal.App("bind-tools-gpu")

# Persistent volume for caching Boltz2 model weights (~3.6 GB).
boltz_weights_volume = modal.Volume.from_name("bind-tools-boltz-weights", create_if_missing=True)

# Mount path inside the container where weights are cached.
BOLTZ_WEIGHTS_MOUNT = "/root/.boltz"

# Default timeouts (seconds).
BOLTZ_TIMEOUT = 1800  # 30 min – diffusion model can be slow
GNINA_TIMEOUT = 600   # 10 min – docking is usually fast
