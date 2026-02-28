"""Protein query layer - resolves protein names to structured data and files."""

from .models import BindingSite, ProteinSearchInput, ResolvedProtein, StructureHit
from .resolver import resolve_protein

__all__ = [
    "BindingSite",
    "StructureHit",
    "ResolvedProtein",
    "ProteinSearchInput",
    "resolve_protein",
]
