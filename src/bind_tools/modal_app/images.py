"""Modal container image definitions for Boltz2 and GNINA."""

from __future__ import annotations

import modal

# Boltz2 image: CUDA-enabled Python 3.11 with boltz and pyyaml.
# Modal base images include CUDA drivers, so torch+CUDA works out of the box.
boltz_image = (
    modal.Image.debian_slim(python_version="3.11")
    .pip_install("boltz", "pyyaml")
)

# GNINA image: reuse the existing Docker Hub image directly.
# add_python injects a Python interpreter for Modal's runtime agent.
gnina_image = (
    modal.Image.from_registry("gnina/gnina:latest", add_python="3.11")
    .pip_install("rdkit-pypi")
)
