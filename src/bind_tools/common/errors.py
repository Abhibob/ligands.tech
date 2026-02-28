"""Exit codes and error hierarchy per specs/common-cli.md."""

from __future__ import annotations

# Exit codes
EXIT_SUCCESS = 0
EXIT_VALIDATION = 2
EXIT_INPUT_MISSING = 3
EXIT_UPSTREAM_FAILURE = 4
EXIT_TIMEOUT = 5
EXIT_PARTIAL = 6
EXIT_UNSUPPORTED = 7


class BindToolError(Exception):
    """Base error for all bind-tool wrappers."""

    exit_code: int = EXIT_UPSTREAM_FAILURE

    def __init__(self, message: str, exit_code: int | None = None):
        super().__init__(message)
        if exit_code is not None:
            self.exit_code = exit_code


class ValidationError(BindToolError):
    exit_code = EXIT_VALIDATION


class InputMissingError(BindToolError):
    exit_code = EXIT_INPUT_MISSING


class UpstreamError(BindToolError):
    exit_code = EXIT_UPSTREAM_FAILURE


class TimeoutError(BindToolError):
    exit_code = EXIT_TIMEOUT


class UnsupportedError(BindToolError):
    exit_code = EXIT_UNSUPPORTED
