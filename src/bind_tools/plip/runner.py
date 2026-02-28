"""PLIP runner: protein-ligand interaction profiling via PLIP library and CLI."""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any

from bind_tools.common.errors import InputMissingError, UpstreamError
from bind_tools.common.runner import ensure_dir, ensure_file, run_subprocess

from .models import PlipProfileSpec, PlipProfileSummary

# ── Optional PLIP import ─────────────────────────────────────────────────────

_PLIP_AVAILABLE = False
try:
    from plip.structure.preparation import PDBComplex  # type: ignore[import-untyped]

    _PLIP_AVAILABLE = True
except ImportError:
    PDBComplex = None  # type: ignore[assignment,misc]


# Interaction attribute names on each PLIP interaction set
_INTERACTION_ATTRS: list[str] = [
    "hbonds_pdon",
    "hbonds_ldon",
    "hydrophobic_contacts",
    "pistacking",
    "pication_laro",
    "pication_paro",
    "saltbridge_lneg",
    "saltbridge_pneg",
    "waterbridge",
    "halogen_bonds",
    "metal_complexes",
]


def check_installed() -> bool:
    """Return True if the PLIP Python library is importable."""
    return _PLIP_AVAILABLE


def check_openbabel_installed() -> bool:
    """Return True if Open Babel CLI (obabel) is found on PATH."""
    return shutil.which("obabel") is not None


# ── Helpers ──────────────────────────────────────────────────────────────────


def _residue_label(res: Any) -> str:
    """Build a human-readable residue label like 'ALA-42-A'."""
    try:
        return f"{res.restype}-{res.resnr}-{res.reschain}"
    except AttributeError:
        return str(res)


def _extract_interactions(interaction_set: Any) -> dict[str, list[dict[str, Any]]]:
    """Extract all interaction types from a single PLIP interaction set."""
    interactions_by_type: dict[str, list[dict[str, Any]]] = {}

    for attr_name in _INTERACTION_ATTRS:
        items = getattr(interaction_set, attr_name, [])
        if not items:
            continue
        records: list[dict[str, Any]] = []
        for item in items:
            record: dict[str, Any] = {"type": attr_name}
            # Extract common fields that most interaction objects carry
            for field in ("restype", "resnr", "reschain", "dist", "angle", "protisdon"):
                val = getattr(item, field, None)
                if val is not None:
                    record[field] = val
            records.append(record)
        interactions_by_type[attr_name] = records

    return interactions_by_type


# ── Main profile runner ──────────────────────────────────────────────────────


def run_profile(spec: PlipProfileSpec, artifacts_dir: Path) -> dict[str, Any]:
    """
    Run PLIP interaction profiling on a PDB complex.

    Returns a dict matching the PlipProfileSummary schema.
    """
    if not _PLIP_AVAILABLE:
        raise UpstreamError(
            "PLIP is not installed. Install with: pip install plip"
        )

    # Resolve the input structure
    if spec.complex_path:
        pdb_path = ensure_file(spec.complex_path, label="complex PDB/mmCIF")
        pdb_text = pdb_path.read_text()
    elif spec.pdb_id:
        # PLIP can fetch by PDB ID — we download via its internal mechanism
        # by writing a minimal wrapper
        pdb_text = _fetch_pdb(spec.pdb_id)
    else:
        raise InputMissingError(
            "Provide either --complex (complexPath) or --pdb-id (pdbId)"
        )

    # Prepare the output directory
    artifacts_dir = ensure_dir(artifacts_dir, label="artifacts directory", create=True)

    # ── Run PLIP analysis ────────────────────────────────────────────────
    mol = PDBComplex()
    mol.load_pdb(pdb_text, as_string=True)
    mol.analyze()

    # Enumerate binding sites
    binding_sites: list[str] = list(mol.interaction_sets.keys())
    selected_site = spec.binding_site

    # If a specific binding site is requested, filter
    if selected_site and selected_site not in binding_sites:
        raise InputMissingError(
            f"Binding site '{selected_site}' not found. "
            f"Available sites: {', '.join(binding_sites)}"
        )

    sites_to_process = [selected_site] if selected_site else binding_sites

    # Aggregate interaction data across selected sites
    all_interactions_by_type: dict[str, list[dict[str, Any]]] = {}
    all_interaction_counts: dict[str, int] = {}
    all_residues: set[str] = set()

    for site_key in sites_to_process:
        iset = mol.interaction_sets[site_key]

        site_interactions = _extract_interactions(iset)

        for itype, records in site_interactions.items():
            all_interactions_by_type.setdefault(itype, []).extend(records)
            all_interaction_counts[itype] = (
                all_interaction_counts.get(itype, 0) + len(records)
            )
            for rec in records:
                restype = rec.get("restype", "")
                resnr = rec.get("resnr", "")
                reschain = rec.get("reschain", "")
                if restype and resnr:
                    all_residues.add(f"{restype}-{resnr}-{reschain}")

    # ── Generate optional artifact outputs via PLIP CLI ──────────────────
    _generate_cli_artifacts(spec, pdb_path if spec.complex_path else None, artifacts_dir)

    # Build the summary
    summary_model = PlipProfileSummary(
        bindingSites=binding_sites,
        selectedBindingSite=selected_site or (binding_sites[0] if binding_sites else ""),
        interactionCounts=all_interaction_counts,
        interactingResidues=sorted(all_residues),
        interactionsByType=all_interactions_by_type,
    )

    return summary_model.model_dump(by_alias=True, mode="json")


# ── PDB fetch helper ────────────────────────────────────────────────────────


def _fetch_pdb(pdb_id: str) -> str:
    """Download a PDB file by its 4-letter ID from the RCSB."""
    import urllib.request

    url = f"https://files.rcsb.org/download/{pdb_id.upper()}.pdb"
    try:
        with urllib.request.urlopen(url, timeout=30) as resp:
            return resp.read().decode("utf-8")
    except Exception as exc:
        raise InputMissingError(
            f"Failed to download PDB {pdb_id} from RCSB: {exc}"
        ) from exc


# ── CLI artifact generation ──────────────────────────────────────────────────


def _generate_cli_artifacts(
    spec: PlipProfileSpec,
    pdb_path: Path | None,
    artifacts_dir: Path,
) -> None:
    """Run the PLIP CLI to generate txt/xml/pymol/pics artifacts if requested."""
    outputs = spec.outputs
    needs_cli = outputs.txt or outputs.xml or outputs.pymol or outputs.pics
    if not needs_cli:
        return

    plip_bin = shutil.which("plip")
    if not plip_bin:
        raise UpstreamError(
            "PLIP CLI binary not found on PATH. "
            "Install with: pip install plip"
        )

    cmd: list[str] = [plip_bin]

    # Input source
    if pdb_path:
        cmd.extend(["-f", str(pdb_path)])
    elif spec.pdb_id:
        cmd.extend(["-i", spec.pdb_id.upper()])

    # Output directory
    cmd.extend(["-o", str(artifacts_dir)])

    # Binding site selection
    if spec.binding_site:
        cmd.extend(["--bindingsite", spec.binding_site])

    # Output format flags
    if outputs.txt:
        cmd.append("-t")
    if outputs.xml:
        cmd.append("-x")
    if outputs.pymol:
        cmd.append("-y")
    if outputs.pics:
        cmd.append("-p")

    # Structure handling flags
    sh = spec.structure_handling
    if sh.no_hydro:
        cmd.append("--nohydro")
    if sh.keep_mod:
        cmd.append("--keepmod")
    if sh.no_fix:
        cmd.append("--nofix")
    for chain in sh.chains:
        cmd.extend(["--chains", chain])
    for residue in sh.residues:
        cmd.extend(["--residues", residue])
    for peptide in sh.peptides:
        cmd.extend(["--peptides", peptide])
    for intra in sh.intra:
        cmd.extend(["--intra", intra])

    result = run_subprocess(cmd, cwd=str(artifacts_dir))

    if result.returncode != 0:
        raise UpstreamError(
            f"PLIP CLI exited with code {result.returncode}: {result.stderr.strip()}"
        )
