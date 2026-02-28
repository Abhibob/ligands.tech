"""Modal GPU cloud integration for bind-tools."""

from __future__ import annotations

import os


def load_dotenv() -> None:
    """Load .env file if python-dotenv is available.

    Looks for .env in the current directory and project root.
    Sets MODAL_TOKEN_ID and MODAL_TOKEN_SECRET (among others) as env vars.
    """
    try:
        from dotenv import load_dotenv as _load_dotenv
    except ImportError:
        return
    _load_dotenv()


def is_modal_available() -> bool:
    """Return True if the modal package is installed and importable."""
    try:
        import modal  # noqa: F401

        return True
    except ImportError:
        return False


def ensure_modal_auth() -> None:
    """Load .env and verify that Modal credentials are configured.

    Raises RuntimeError if neither a Modal token file (~/.modal.toml)
    nor MODAL_TOKEN_ID/MODAL_TOKEN_SECRET env vars are found.
    """
    load_dotenv()

    # Modal SDK picks up these env vars automatically
    has_env_token = (
        os.environ.get("MODAL_TOKEN_ID") and os.environ.get("MODAL_TOKEN_SECRET")
    )

    if has_env_token:
        return

    # Check for ~/.modal.toml (created by `modal token new`)
    modal_toml = os.path.expanduser("~/.modal.toml")
    if os.path.isfile(modal_toml):
        return

    raise RuntimeError(
        "Modal credentials not found. Either:\n"
        "  1. Run `modal token new` (interactive browser login), or\n"
        "  2. Set MODAL_TOKEN_ID and MODAL_TOKEN_SECRET in your environment or .env file.\n"
        "  See MODAL_DEPLOYMENT.md for details."
    )
