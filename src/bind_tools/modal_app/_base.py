"""Base Modal app definition, volume, and constants.

Other modules import from here to avoid circular imports.
app.py (the deploy entry-point) re-exports everything and
imports the remote classes so Modal registers them.
"""

from __future__ import annotations

import modal

app = modal.App("bind-tools-gpu")

# Persistent volume for caching Boltz2 model weights (~3.6 GB).
boltz_weights_volume = modal.Volume.from_name("bind-tools-boltz-weights", create_if_missing=True)

# Mount path inside the container where weights are cached.
BOLTZ_WEIGHTS_MOUNT = "/root/.boltz"

# Default timeouts (seconds).
BOLTZ_TIMEOUT = 1800  # 30 min – diffusion model can be slow
GNINA_TIMEOUT = 600   # 10 min – docking is usually fast
SEARCH_TIMEOUT = 120  # 2 min
