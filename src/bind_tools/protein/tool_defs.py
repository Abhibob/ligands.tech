"""OpenRouter tool definition for protein resolution."""

PROTEIN_RESOLVE_TOOL = {
    "type": "function",
    "function": {
        "name": "protein_resolve",
        "description": (
            "Resolve a protein name, gene name, or UniProt ID into structured "
            "data needed for binding analysis. Returns: UniProt accession, FASTA "
            "sequence path, ranked PDB crystal structures with ligands, known "
            "binding site residues, and downloaded structure files. Use this "
            "before running bind-boltz or bind-gnina when you only have a "
            "protein name."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": (
                        "Protein name (e.g. 'EGFR', 'epidermal growth factor "
                        "receptor'), gene name, or UniProt accession (e.g. "
                        "'P00533')"
                    ),
                },
                "organism": {
                    "type": "string",
                    "description": "Target organism",
                    "default": "Homo sapiens",
                },
                "max_structures": {
                    "type": "integer",
                    "description": "Maximum PDB structures to return",
                    "default": 5,
                },
            },
            "required": ["query"],
        },
    },
}
