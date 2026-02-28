"""File serialisation helpers for shipping files to/from Modal containers."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass
class FilePayload:
    """A file represented as a name + raw bytes for network transfer."""

    name: str
    data: bytes


def read_file_payload(path: str | Path) -> FilePayload:
    """Read a local file into a FilePayload."""
    p = Path(path)
    return FilePayload(name=p.name, data=p.read_bytes())


def write_file_payload(payload: FilePayload, dest_dir: str | Path) -> Path:
    """Write a FilePayload to *dest_dir* and return the written path."""
    dest = Path(dest_dir) / payload.name
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(payload.data)
    return dest


# ── Input collectors ─────────────────────────────────────────────────────────


def collect_input_files_boltz(
    spec_dict: dict,
) -> list[FilePayload]:
    """Gather all local input files referenced by a Boltz upstream YAML dict.

    This reads protein FASTA/PDB/CIF and ligand SDF/MOL2 files that appear
    in the ``sequences`` list of the upstream dict.
    """
    payloads: list[FilePayload] = []
    for seq_entry in spec_dict.get("sequences", []):
        for kind in ("protein", "ligand"):
            block = seq_entry.get(kind)
            if not block:
                continue
            for key in ("fasta", "pdb", "cif", "sdf", "mol2"):
                file_path = block.get(key)
                if file_path and Path(file_path).is_file():
                    payloads.append(read_file_payload(file_path))
    return payloads


def collect_input_files_gnina(
    receptor_path: str,
    ligand_paths: list[str],
    autobox_ligand_path: str | None = None,
) -> list[FilePayload]:
    """Gather receptor, ligand, and autobox-ligand files for GNINA."""
    payloads: list[FilePayload] = []
    payloads.append(read_file_payload(receptor_path))
    for lp in ligand_paths:
        payloads.append(read_file_payload(lp))
    if autobox_ligand_path:
        # Avoid duplicating if autobox is the same file as a ligand
        existing_names = {p.name for p in payloads}
        ab = read_file_payload(autobox_ligand_path)
        if ab.name not in existing_names:
            payloads.append(ab)
    return payloads
