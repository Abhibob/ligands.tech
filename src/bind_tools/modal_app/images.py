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

# Reranker image: BGE reranker for search result reranking.
# .run_commands() bakes model weights (~1.1 GB) into the image to avoid cold-start downloads.
reranker_image = (
    modal.Image.debian_slim(python_version="3.11")
    .pip_install(
        "FlagEmbedding>=1.2.0",
        "torch>=2.0.0",
        "transformers>=4.33.0,<4.46.0",
        "httpx>=0.27.0",
    )
    .run_commands(
        "python -c \"from FlagEmbedding import FlagReranker; FlagReranker('BAAI/bge-reranker-v2-m3')\""
    )
)
