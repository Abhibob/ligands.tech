"""OpenRouter tool definition for ligand resolution."""

LIGAND_RESOLVE_TOOL = {
    "type": "function",
    "function": {
        "name": "ligand_resolve",
        "description": (
            "Resolve a ligand name, SMILES string, or PubChem CID into structured "
            "data needed for binding analysis. Returns: SMILES strings, molecular "
            "properties (MW, LogP, etc.), 3D SDF file paths, and chemical identifiers "
            "(PubChem CID, InChI Key). Use this before running bind-boltz or bind-gnina "
            "when you only have a ligand name or chemical structure."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": (
                        "Ligand name (e.g., 'erlotinib', 'aspirin'), SMILES string "
                        "(e.g., 'CCO'), or PubChem CID with 'CID:' prefix (e.g., 'CID:176870')"
                    ),
                },
                "generate_3d": {
                    "type": "boolean",
                    "description": "Generate 3D coordinates (default: true)",
                    "default": True,
                },
            },
            "required": ["query"],
        },
    },
}
