"""Modal deploy entry-point for bind-tools-gpu.

Run:  modal deploy src/bind_tools/modal_app/app.py
"""

from __future__ import annotations

from bind_tools.modal_app import ensure_modal_auth

ensure_modal_auth()

# Re-export the app and shared objects so existing imports still work.
from bind_tools.modal_app._base import (  # noqa: F401
    app,
    boltz_weights_volume,
    BOLTZ_WEIGHTS_MOUNT,
    BOLTZ_TIMEOUT,
    GNINA_TIMEOUT,
)

# Import remote classes so Modal registers them with the app on deploy.
from bind_tools.modal_app.boltz_remote import BoltzPredictor  # noqa: F401
from bind_tools.modal_app.gnina_remote import GninaRunner  # noqa: F401
from bind_tools.modal_app.web_api import WebAPI  # noqa: F401
