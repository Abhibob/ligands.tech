"""PoseBusters runner: validate docked poses using the posebusters library."""

from __future__ import annotations

from pathlib import Path

from bind_tools.common.errors import InputMissingError, UpstreamError
from bind_tools.common.runner import ensure_file

from .models import PoseBustersCheckSpec, PoseBustersPoseSummary

try:
    import posebusters as _pb_module

    POSEBUSTERS_INSTALLED = True
except ImportError:
    _pb_module = None
    POSEBUSTERS_INSTALLED = False


# Failure severity categories
FATAL_CHECKS = frozenset({
    "sanitization",
    "all_atoms_connected",
})

MAJOR_CHECKS = frozenset({
    "bond_lengths",
    "bond_angles",
    "internal_steric_clash",
    "volume_overlap_with_protein",
})

# Everything else is minor


def check_installed() -> bool:
    """Return True if posebusters is importable."""
    return POSEBUSTERS_INSTALLED


def get_version() -> str:
    """Return the posebusters version string, or 'not installed'."""
    if _pb_module is None:
        return "not installed"
    return getattr(_pb_module, "__version__", "unknown")


def _categorize_failure(check_name: str) -> str:
    """Categorize a check name into fatal, major, or minor."""
    if check_name in FATAL_CHECKS:
        return "fatal"
    if check_name in MAJOR_CHECKS:
        return "major"
    return "minor"


def _dataframe_to_summary(df, pose_path: str) -> PoseBustersPoseSummary:
    """Convert a PoseBusters DataFrame result into a PoseBustersPoseSummary."""
    # The DataFrame has boolean columns for each check
    # Flatten the multi-index columns if present
    if hasattr(df.columns, "levels"):
        # Multi-level columns: flatten to just the check names
        df.columns = ["_".join(str(c) for c in col).strip("_") if isinstance(col, tuple) else col for col in df.columns]

    fatal_failures: list[str] = []
    major_failures: list[str] = []
    minor_failures: list[str] = []
    failed_checks: list[str] = []

    total_checks = 0
    passed_checks = 0

    for col in df.columns:
        # Skip non-boolean columns
        val = df[col].iloc[0] if len(df) > 0 else None
        if not isinstance(val, (bool,)):
            # Try to interpret numpy bool
            try:
                import numpy as np

                if not isinstance(val, (np.bool_,)):
                    continue
            except ImportError:
                continue

        total_checks += 1
        if val:
            passed_checks += 1
        else:
            failed_checks.append(col)
            category = _categorize_failure(col)
            if category == "fatal":
                fatal_failures.append(col)
            elif category == "major":
                major_failures.append(col)
            else:
                minor_failures.append(col)

    passes_all = len(failed_checks) == 0
    pass_fraction = passed_checks / total_checks if total_checks > 0 else 0.0

    return PoseBustersPoseSummary(
        inputPath=pose_path,
        passesAllChecks=passes_all,
        passFraction=round(pass_fraction, 4),
        fatalFailures=fatal_failures,
        majorFailures=major_failures,
        minorFailures=minor_failures,
        failedChecks=failed_checks,
    )


def run_check(spec: PoseBustersCheckSpec) -> list[PoseBustersPoseSummary]:
    """Run PoseBusters validation on all predicted poses in the spec.

    Returns a list of PoseBustersPoseSummary, one per pose.
    """
    if not POSEBUSTERS_INSTALLED:
        raise UpstreamError(
            "posebusters is not installed. Install it with: pip install posebusters"
        )

    from posebusters import PoseBusters

    # Validate input files
    protein_path: str | None = None
    reference_path: str | None = None

    if spec.protein_path:
        protein_path = str(ensure_file(spec.protein_path, "protein"))
    if spec.reference_ligand_path:
        reference_path = str(ensure_file(spec.reference_ligand_path, "reference ligand"))

    # Determine config
    config = spec.config
    if config == "auto":
        if protein_path and reference_path:
            config = "redock"
        elif protein_path:
            config = "dock"
        else:
            config = "mol"

    summaries: list[PoseBustersPoseSummary] = []

    for pose_path_str in spec.predicted_poses:
        pose_file = ensure_file(pose_path_str, "predicted pose")

        try:
            pb = PoseBusters(config=config)

            bust_kwargs: dict = {
                "mol_pred": str(pose_file),
                "full_report": spec.full_report,
            }
            if protein_path:
                bust_kwargs["mol_cond"] = protein_path
            if reference_path:
                bust_kwargs["mol_true"] = reference_path

            df = pb.bust(**bust_kwargs)

            summary = _dataframe_to_summary(df, str(pose_file))
            summaries.append(summary)
        except Exception as exc:
            # If a single pose fails, record it as a failed summary rather than aborting all
            summaries.append(
                PoseBustersPoseSummary(
                    inputPath=str(pose_file),
                    passesAllChecks=False,
                    passFraction=0.0,
                    fatalFailures=[f"error: {exc}"],
                    majorFailures=[],
                    minorFailures=[],
                    failedChecks=[f"error: {exc}"],
                )
            )

    return summaries
