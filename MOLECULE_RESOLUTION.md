# Molecule Resolution: Fetching Proteins, Ligands, and Structures

> Reference for the CLI tool layer and the visualizer team.
> Covers every API needed to go from a user typing "EGFR" or "erlotinib" to actual downloadable structure files.

---

## Table of Contents

1. [The Problem](#1-the-problem)
2. [Resolution Chains](#2-resolution-chains)
3. [Protein APIs](#3-protein-apis)
4. [Ligand / Small Molecule APIs](#4-ligand--small-molecule-apis)
5. [Structure File Downloads](#5-structure-file-downloads)
6. [Target → Known Binders (Drug Discovery Queries)](#6-target--known-binders)
7. [Local Generation (RDKit)](#7-local-generation-rdkit)
8. [Proposed `bind-resolve` CLI Tool](#8-proposed-bind-resolve-cli-tool)
9. [Visualizer Integration Notes](#9-visualizer-integration-notes)
10. [Quick Reference Table](#10-quick-reference-table)

---

## 1. The Problem

Users will say things like:

- "Does erlotinib bind EGFR?"
- "Screen these SMILES against CDK2"
- "Show me the p53 structure"
- "What drugs target human BRAF V600E?"

We need to resolve these to actual files:

| User says | We need | Format |
|-----------|---------|--------|
| "EGFR" | 3D protein structure | PDB / CIF |
| "erlotinib" | 3D ligand structure | SDF |
| "CC(=O)OC1=CC=CC=C1C(=O)O" | 3D ligand with coordinates | SDF |
| "P00533" | Protein structure by UniProt ID | PDB / CIF |
| "1M17" | Protein-ligand complex | PDB / CIF |
| "ATP" | Ligand by CCD 3-letter code | SDF |

Every tool in the CLI layer needs resolved file paths. Agents will call a resolution step before invoking `bind-boltz`, `bind-gnina`, etc.

---

## 2. Resolution Chains

### Protein: Name → Structure

```
User input ("EGFR", "human p53", "CDK2")
    │
    ▼
[UniProt Search API]
    query=(gene:EGFR) AND (organism_id:9606) AND (reviewed:true)
    → P00533  (canonical UniProt accession)
    → full amino acid sequence
    → gene synonyms (ERBB, ERBB1, HER1)
    │
    ├──► [PDBe Best Structures API]
    │      /mappings/best_structures/P00533
    │      → ranked list: 8A27 (1.07Å), 5UG9 (1.22Å), ...
    │      │
    │      └──► [RCSB Download]
    │             files.rcsb.org/download/8A27.cif
    │             → experimental structure (PDB/CIF)
    │
    └──► [AlphaFold API]  (fallback: no experimental structure, or need full-length)
           alphafold.ebi.ac.uk/api/prediction/P00533
           → AF-P00533-F1-model_v6.cif (predicted, full-length)
```

### Ligand: Name → SDF

```
User input ("erlotinib", "aspirin", SMILES string)
    │
    ├── Is it a SMILES string?
    │     └──► [RDKit] EmbedMolecule + MMFF optimize → 3D SDF (local, instant)
    │
    ├── Is it a CCD 3-letter code? ("ATP", "SAH")
    │     └──► [RCSB Ligand Expo]
    │           files.rcsb.org/ligands/download/ATP_ideal.sdf
    │           → ideal 3D coordinates
    │
    └── Is it a drug/compound name?
          └──► [PubChem PUG-REST]
                /compound/name/erlotinib/record/SDF?record_type=3d
                → 3D SDF with OEChem-generated coordinates
```

### Target → Known Ligands (drug discovery)

```
Protein name ("EGFR")
    │
    ▼
[UniProt Search] → P00533
    │
    ▼
[ChEMBL Target API]
    /target.json?target_components__accession=P00533
    → CHEMBL203 (target ID)
    │
    ▼
[ChEMBL Activity API]
    /activity.json?target_chembl_id=CHEMBL203&pchembl_value__gte=6
    → all compounds with IC50 < 1µM
    → SMILES for each hit
    │
    ▼
[ChEMBL Mechanism API]
    /mechanism.json?target_chembl_id=CHEMBL203
    → approved drugs: erlotinib, gefitinib, cetuximab, ...
```

---

## 3. Protein APIs

### 3.1 UniProt Search (name/gene → accession + sequence)

**Endpoint**: `GET https://rest.uniprot.org/uniprotkb/search`

**CORS**: Yes (`Access-Control-Allow-Origin: *`)

**Auth**: None required

**Query parameters**:

| Param | Description | Example |
|-------|-------------|---------|
| `query` | Solr-style query | `(gene:EGFR) AND (organism_id:9606) AND (reviewed:true)` |
| `fields` | Return fields | `accession,gene_names,protein_name,organism_name,xref_pdb,sequence` |
| `format` | `json`, `tsv`, `fasta` | `json` |
| `size` | Results per page (max 500) | `5` |

**Example — resolve "EGFR human"**:

```
GET https://rest.uniprot.org/uniprotkb/search?query=(gene:EGFR)+AND+(organism_id:9606)+AND+(reviewed:true)&fields=accession,gene_names,protein_name,organism_name,xref_pdb,sequence&format=json&size=1
```

**Response** (trimmed):

```json
{
  "results": [{
    "primaryAccession": "P00533",
    "proteinDescription": {
      "recommendedName": {
        "fullName": { "value": "Epidermal growth factor receptor" }
      }
    },
    "genes": [{
      "geneName": { "value": "EGFR" },
      "synonyms": [
        { "value": "ERBB" },
        { "value": "ERBB1" },
        { "value": "HER1" }
      ]
    }],
    "sequence": {
      "value": "MRPSGTAGAALLALLAALCPASRALEEKKVCQGTSNKLTQLGTFEDHF...",
      "length": 1210
    },
    "uniProtKBCrossReferences": [
      {
        "database": "PDB",
        "id": "1M17",
        "properties": [
          { "key": "Method", "value": "X-ray" },
          { "key": "Resolution", "value": "2.60 A" },
          { "key": "Chains", "value": "A=695-1022" }
        ]
      }
    ]
  }]
}
```

**Common organism taxonomy IDs**:

| Organism | ID |
|----------|-----|
| Human | 9606 |
| Mouse | 10090 |
| Rat | 10116 |
| E. coli | 562 |
| S. cerevisiae | 559292 |

### 3.2 PDBe Best Structures (UniProt → ranked PDB list)

**Endpoint**: `GET https://www.ebi.ac.uk/pdbe/graph-api/mappings/best_structures/{uniprot_accession}`

**CORS**: Yes

This returns PDB entries **ranked by quality** (resolution, coverage, method).

```
GET https://www.ebi.ac.uk/pdbe/graph-api/mappings/best_structures/P00533
```

**Response** (trimmed):

```json
{
  "P00533": [
    {
      "pdb_id": "8a27",
      "chain_id": "A",
      "experimental_method": "X-ray diffraction",
      "resolution": 1.07,
      "tax_id": 9606,
      "unp_start": 700,
      "unp_end": 1022,
      "coverage": 0.271
    },
    {
      "pdb_id": "7syd",
      "chain_id": "A",
      "experimental_method": "Electron Microscopy",
      "resolution": 3.1,
      "unp_start": 1,
      "unp_end": 1210,
      "coverage": 1.0
    }
  ]
}
```

**Selection heuristics for our tools**:

| Use case | Pick by |
|----------|---------|
| Docking (bind-gnina) | Highest resolution covering the binding domain |
| Full structure view | Highest coverage |
| No experimental data | AlphaFold fallback |

### 3.3 RCSB PDB Search (advanced structure search)

**Endpoint**: `POST https://search.rcsb.org/rcsbsearch/v2/query`

**CORS**: Yes

**Example — all human EGFR structures sorted by resolution**:

```json
{
  "query": {
    "type": "group",
    "logical_operator": "and",
    "nodes": [
      {
        "type": "terminal",
        "service": "text",
        "parameters": {
          "attribute": "rcsb_entity_source_organism.rcsb_gene_name.value",
          "operator": "exact_match",
          "value": "EGFR"
        }
      },
      {
        "type": "terminal",
        "service": "text",
        "parameters": {
          "attribute": "rcsb_entity_source_organism.taxonomy_lineage.id",
          "operator": "exact_match",
          "value": "9606"
        }
      }
    ]
  },
  "return_type": "entry",
  "request_options": {
    "paginate": { "start": 0, "rows": 10 },
    "sort": [{ "sort_by": "rcsb_entry_info.resolution_combined", "direction": "asc" }]
  }
}
```

**Response**: `{ "total_count": 348, "result_set": [{ "identifier": "8A27" }, ...] }`

**Search by UniProt ID** (simpler):

```json
{
  "query": {
    "type": "terminal",
    "service": "text",
    "parameters": {
      "attribute": "rcsb_polymer_entity_container_identifiers.uniprot_ids",
      "operator": "exact_match",
      "value": "P00533"
    }
  },
  "return_type": "entry"
}
```

### 3.4 PDB ↔ UniProt Mapping (SIFTS)

**PDB → UniProt**:

```
GET https://www.ebi.ac.uk/pdbe/api/mappings/uniprot/{pdb_id}
```

Returns chain-level mapping with residue ranges and sequence identity.

**UniProt → PDB (batch via ID Mapping)**:

```
POST https://rest.uniprot.org/idmapping/run
Body: from=UniProtKB_AC-ID&to=PDB&ids=P00533
→ { "jobId": "abc123" }

GET https://rest.uniprot.org/idmapping/results/abc123
→ [{ "from": "P00533", "to": "1M17" }, ...]
```

### 3.5 AlphaFold Predicted Structures

**Endpoint**: `GET https://alphafold.ebi.ac.uk/api/prediction/{uniprot_accession}`

**CORS**: Yes

**Response**:

```json
{
  "cifUrl": "https://alphafold.ebi.ac.uk/files/AF-P00533-F1-model_v6.cif",
  "pdbUrl": "https://alphafold.ebi.ac.uk/files/AF-P00533-F1-model_v6.pdb",
  "bcifUrl": "https://alphafold.ebi.ac.uk/files/AF-P00533-F1-model_v6.bcif",
  "gene": "EGFR",
  "uniprotAccession": "P00533",
  "uniprotDescription": "Epidermal growth factor receptor",
  "globalMetricValue": 75.94
}
```

**Direct download** (if you know the UniProt ID):

```
https://alphafold.ebi.ac.uk/files/AF-{UNIPROT_ID}-F1-model_v6.cif
https://alphafold.ebi.ac.uk/files/AF-{UNIPROT_ID}-F1-model_v6.pdb
https://alphafold.ebi.ac.uk/files/AF-{UNIPROT_ID}-F1-model_v6.bcif
```

Fragments: for proteins > 2700 residues, F1 covers 1-1400, F2 covers 201-1600, etc.

### 3.6 ESMFold (real-time sequence → structure)

**Endpoint**: `POST https://api.esmatlas.com/foldSequence/v1/pdb/`

**Content-Type**: `text/plain`

**Body**: Raw amino acid sequence

**Response**: PDB-format text

```bash
curl -X POST https://api.esmatlas.com/foldSequence/v1/pdb/ \
  -d "MLEICLKLVGCKSKKGLSSSSSCYLE"
```

Limit: ~400 residues. No auth. Response in seconds. Less accurate than AlphaFold/Boltz but instant.

---

## 4. Ligand / Small Molecule APIs

### 4.1 PubChem PUG-REST (primary source)

**Base URL**: `https://pubchem.ncbi.nlm.nih.gov/rest/pug`

**CORS**: Yes (`Access-Control-Allow-Origin: *`)

**Rate limit**: 5 req/sec

#### Name → CID

```
GET /compound/name/{name}/cids/JSON
```

```
https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/name/erlotinib/cids/JSON
→ { "IdentifierList": { "CID": [176870] } }
```

#### Name → 3D SDF (one-step)

```
GET /compound/name/{name}/record/SDF?record_type=3d
```

```
https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/name/erlotinib/record/SDF?record_type=3d
→ V2000 SDF with full 3D coordinates
```

#### Name → 2D SDF

```
GET /compound/name/{name}/record/SDF
```

#### CID → 3D SDF

```
GET /compound/cid/{cid}/record/SDF?record_type=3d
```

#### Name → SMILES + properties

```
GET /compound/name/{name}/property/{properties}/JSON
```

```
https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/name/erlotinib/property/IsomericSMILES,MolecularFormula,MolecularWeight/JSON
→ {
    "PropertyTable": {
      "Properties": [{
        "CID": 176870,
        "MolecularFormula": "C22H23N3O4",
        "MolecularWeight": "393.4",
        "IsomericSMILES": "C#Cc1cccc(Nc2ncnc3cc(OCCOC)c(OCCOC)cc23)c1"
      }]
    }
  }
```

#### SMILES → CID

```
GET /compound/smiles/{smiles}/cids/JSON
```

#### Batch (multiple CIDs)

```
GET /compound/cid/2244,5245,2662/property/CanonicalSMILES,MolecularFormula/JSON
```

Note: batch by name does NOT work — resolve names to CIDs first, then batch by CID.

#### 3D Conformers

```
GET /compound/cid/{cid}/conformers/JSON        → list conformer IDs
GET /conformers/{conformer_id}/SDF              → download specific conformer
```

#### Available properties

`MolecularFormula`, `MolecularWeight`, `CanonicalSMILES`, `IsomericSMILES`, `InChI`, `InChIKey`, `IUPACName`, `XLogP`, `ExactMass`, `TPSA`, `Complexity`, `Charge`, `HBondDonorCount`, `HBondAcceptorCount`, `RotatableBondCount`, `HeavyAtomCount`, `Volume3D`

### 4.2 RCSB Ligand Expo / CCD (crystallographic ligands)

For 3-letter CCD codes found in PDB entries (ATP, SAH, HEM, etc.):

#### Ideal coordinates (geometry-optimized)

```
GET https://files.rcsb.org/ligands/download/{CCD_ID}_ideal.sdf
```

```
https://files.rcsb.org/ligands/download/ATP_ideal.sdf
https://files.rcsb.org/ligands/download/SAH_ideal.sdf
```

#### Experimental coordinates from a specific PDB entry

```
GET https://models.rcsb.org/v1/{pdb_id}/ligand?label_comp_id={CCD_ID}&encoding=sdf
```

```
https://models.rcsb.org/v1/1M17/ligand?label_comp_id=AQ4&encoding=sdf
```

This gives you the ligand as it actually sits in the crystal structure — essential for understanding binding pose.

### 4.3 ChEMBL (molecules with bioactivity data)

**Base URL**: `https://www.ebi.ac.uk/chembl/api/data`

**CORS**: Yes

#### Get molecule as SDF

```
GET /molecule/{CHEMBL_ID}?format=sdf
```

```
https://www.ebi.ac.uk/chembl/api/data/molecule/CHEMBL553?format=sdf
→ RDKit-generated 2D SDF for erlotinib
```

#### Search by name

```
GET /molecule/search.json?q=erlotinib
```

#### Get molecule JSON (SMILES, properties, clinical phase)

```
GET /molecule/CHEMBL553.json
→ {
    "pref_name": "ERLOTINIB",
    "max_phase": 4.0,
    "molecule_structures": {
      "canonical_smiles": "C#Cc1cccc(Nc2ncnc3cc(OCCOC)c(OCCOC)cc23)c1"
    },
    "molecule_properties": {
      "alogp": "3.20",
      "hba": 7,
      "hbd": 1,
      "psa": "74.73",
      "mw_freebase": "393.44",
      "qed_weighted": "0.62"
    }
  }
```

---

## 5. Structure File Downloads

### 5.1 Protein structures

| Source | Format | URL | Speed |
|--------|--------|-----|-------|
| RCSB PDB | BinaryCIF | `https://models.rcsb.org/{PDBID}.bcif` | Fastest (CDN) |
| RCSB PDB | mmCIF | `https://files.rcsb.org/download/{PDBID}.cif` | Fast |
| RCSB PDB | PDB (legacy) | `https://files.rcsb.org/download/{PDBID}.pdb` | Fast |
| PDBe | BinaryCIF | `https://www.ebi.ac.uk/pdbe/entry-files/download/{PDBID}.bcif` | Fast (EU) |
| PDBe | Updated CIF | `https://www.ebi.ac.uk/pdbe/entry-files/download/{PDBID}_updated.cif` | Has SIFTS annotations |
| AlphaFold | BinaryCIF | `https://alphafold.ebi.ac.uk/files/AF-{UNIPROT}-F1-model_v6.bcif` | Fast |
| AlphaFold | mmCIF | `https://alphafold.ebi.ac.uk/files/AF-{UNIPROT}-F1-model_v6.cif` | Fast |
| AlphaFold | PDB | `https://alphafold.ebi.ac.uk/files/AF-{UNIPROT}-F1-model_v6.pdb` | Fast |

All are CORS-enabled. No auth required.

**For the visualizer**: prefer BinaryCIF (5-10x smaller than text CIF).

**For CLI tools**: prefer mmCIF or PDB (easier to parse, pass to downstream tools).

### 5.2 Ligand structures

| Source | Format | URL | When to use |
|--------|--------|-----|-------------|
| PubChem | 3D SDF | `/compound/name/{name}/record/SDF?record_type=3d` | Drug/compound by name |
| PubChem | 2D SDF | `/compound/name/{name}/record/SDF` | When 3D not needed |
| RCSB CCD | Ideal SDF | `files.rcsb.org/ligands/download/{CCD}_ideal.sdf` | PDB ligand by 3-letter code |
| RCSB Model | Exp. SDF | `models.rcsb.org/v1/{PDBID}/ligand?label_comp_id={CCD}&encoding=sdf` | Ligand as in crystal structure |
| ChEMBL | 2D SDF | `/molecule/{CHEMBL_ID}?format=sdf` | By ChEMBL ID |
| RDKit | 3D SDF | Local generation from SMILES | When you have SMILES only |

### 5.3 Biological assemblies

```
https://files.rcsb.org/download/{PDBID}-assembly{N}.cif
```

---

## 6. Target → Known Binders

### 6.1 Resolution chain

```
Protein name
    → UniProt accession (section 3.1)
    → ChEMBL target ID (section 6.2)
    → Bioactivity data (section 6.3)
    → Approved drugs (section 6.4)
```

### 6.2 UniProt → ChEMBL target

```
GET https://www.ebi.ac.uk/chembl/api/data/target.json?target_components__accession=P00533
→ { "targets": [{ "target_chembl_id": "CHEMBL203", "pref_name": "Epidermal growth factor receptor" }] }
```

### 6.3 Target → active compounds

```
GET https://www.ebi.ac.uk/chembl/api/data/activity.json?target_chembl_id=CHEMBL203&pchembl_value__gte=6&limit=20
```

`pchembl_value >= 6` means IC50/Ki/Kd < 1µM. Each result includes:

```json
{
  "molecule_chembl_id": "CHEMBL68920",
  "canonical_smiles": "Cc1cc(C)c(...)[nH]1",
  "standard_type": "IC50",
  "standard_value": "41.0",
  "standard_units": "nM",
  "pchembl_value": "7.39"
}
```

### 6.4 Target → approved drugs

```
GET https://www.ebi.ac.uk/chembl/api/data/mechanism.json?target_chembl_id=CHEMBL203
```

Returns drugs with mechanism of action:

| ChEMBL ID | Drug | Phase | Action |
|-----------|------|-------|--------|
| CHEMBL553 | Erlotinib | 4 (approved) | Inhibitor |
| CHEMBL939 | Gefitinib | 4 (approved) | Inhibitor |
| CHEMBL1201827 | Panitumumab | 4 (approved) | Inhibitor |
| CHEMBL1201577 | Cetuximab | 4 (approved) | Inhibitor |

### 6.5 ChEMBL filter syntax

Pattern: `field__operator=value`

| Operator | Meaning | Example |
|----------|---------|---------|
| `exact` | Exact match | `pref_name__exact=Erlotinib` |
| `icontains` | Case-insensitive substring | `pref_name__icontains=kinase` |
| `gte` / `lte` | >= / <= | `pchembl_value__gte=6` |
| `in` | Value in set | `max_phase__in=3,4` |
| `isnull` | Null check | `pchembl_value__isnull=false` |

Pagination: `page_meta.next` for next page, `&limit=1000` for max page size.

---

## 7. Local Generation (RDKit)

When you have a SMILES string and need a 3D SDF file — no API call needed.

### SMILES → 3D SDF

```python
from rdkit import Chem
from rdkit.Chem import AllChem

mol = Chem.MolFromSmiles("C#Cc1cccc(Nc2ncnc3cc(OCCOC)c(OCCOC)cc23)c1")  # erlotinib
mol = Chem.AddHs(mol)
AllChem.EmbedMolecule(mol, AllChem.ETKDGv3())  # ETKDG conformer generation
AllChem.MMFFOptimizeMolecule(mol)               # MMFF94 energy minimization

writer = Chem.SDWriter("erlotinib_3d.sdf")
writer.write(mol)
writer.close()
```

### Multiple conformers

```python
mol = Chem.AddHs(Chem.MolFromSmiles("C#Cc1cccc(Nc2ncnc3cc(OCCOC)c(OCCOC)cc23)c1"))
params = AllChem.ETKDGv3()
params.numThreads = 4
cids = AllChem.EmbedMultipleConfs(mol, numConfs=10, params=params)
for cid in cids:
    AllChem.MMFFOptimizeMolecule(mol, confId=cid)
```

### Format conversions

```python
# SMILES → InChI
Chem.MolToInchi(mol)

# SDF → SMILES
for mol in Chem.SDMolSupplier("input.sdf"):
    print(Chem.MolToSmiles(mol))

# SMILES → 2D MOL block
mol2d = Chem.MolFromSmiles("CCO")
AllChem.Compute2DCoords(mol2d)
Chem.MolToMolBlock(mol2d)
```

---

## 8. Proposed `bind-resolve` CLI Tool

A new wrapper that handles all molecule resolution for the agent and other CLI tools.

### Subcommands

```bash
# Resolve a protein name → best structure files
bind-resolve protein --name "EGFR" --organism human --json-out result.json

# Resolve a protein by UniProt accession
bind-resolve protein --uniprot P00533 --json-out result.json

# Resolve a ligand name → 3D SDF
bind-resolve ligand --name "erlotinib" --json-out result.json

# Resolve a ligand from SMILES → 3D SDF
bind-resolve ligand --smiles "C#Cc1cccc(Nc2ncnc3cc(OCCOC)c(OCCOC)cc23)c1" --json-out result.json

# Resolve a CCD code → SDF
bind-resolve ligand --ccd ATP --json-out result.json

# Search for structures of a protein
bind-resolve search --gene EGFR --organism human --json-out result.json

# Find known binders for a target
bind-resolve binders --gene EGFR --organism human --min-pchembl 6 --json-out result.json

# Extract ligand from a PDB entry
bind-resolve extract-ligand --pdb-id 1M17 --ccd AQ4 --json-out result.json

# Doctor
bind-resolve doctor
```

### Result envelope for `bind-resolve protein`

```json
{
  "apiVersion": "binding.dev/v1",
  "kind": "ResolveProteinResult",
  "metadata": { "requestId": "resolve-001", "createdAt": "2026-02-27T12:00:00Z" },
  "tool": "resolve",
  "wrapperVersion": "0.1.0",
  "status": "succeeded",
  "summary": {
    "query": { "name": "EGFR", "organism": "human", "organismId": 9606 },
    "uniprot": {
      "accession": "P00533",
      "name": "Epidermal growth factor receptor",
      "gene": "EGFR",
      "synonyms": ["ERBB", "ERBB1", "HER1"],
      "sequenceLength": 1210,
      "sequence": "MRPSGTAGAALLALLAALCPASRALEEKKVCQ..."
    },
    "bestStructures": [
      {
        "pdbId": "8A27",
        "method": "X-ray diffraction",
        "resolution": 1.07,
        "chain": "A",
        "coverage": 0.271,
        "uniprotRange": "700-1022",
        "downloadUrl": "https://files.rcsb.org/download/8A27.cif"
      }
    ],
    "alphafold": {
      "available": true,
      "cifUrl": "https://alphafold.ebi.ac.uk/files/AF-P00533-F1-model_v6.cif",
      "pdbUrl": "https://alphafold.ebi.ac.uk/files/AF-P00533-F1-model_v6.pdb",
      "confidence": 75.94
    },
    "totalStructures": 348
  },
  "artifacts": {
    "downloadedStructure": "/workspace/resolved/8A27.cif",
    "downloadedSequence": "/workspace/resolved/P00533.fasta"
  }
}
```

### Result envelope for `bind-resolve ligand`

```json
{
  "apiVersion": "binding.dev/v1",
  "kind": "ResolveLigandResult",
  "metadata": { "requestId": "resolve-002", "createdAt": "2026-02-27T12:00:00Z" },
  "summary": {
    "query": { "name": "erlotinib" },
    "resolved": {
      "name": "Erlotinib",
      "pubchemCid": 176870,
      "chemblId": "CHEMBL553",
      "smiles": "C#Cc1cccc(Nc2ncnc3cc(OCCOC)c(OCCOC)cc23)c1",
      "inchiKey": "AAKJLRGGTJKAMG-UHFFFAOYSA-N",
      "molecularFormula": "C22H23N3O4",
      "molecularWeight": 393.4,
      "maxClinicalPhase": 4
    }
  },
  "artifacts": {
    "sdf3d": "/workspace/resolved/erlotinib_3d.sdf",
    "sdf2d": "/workspace/resolved/erlotinib_2d.sdf"
  }
}
```

### Result envelope for `bind-resolve binders`

```json
{
  "apiVersion": "binding.dev/v1",
  "kind": "ResolveBinders Result",
  "summary": {
    "target": { "gene": "EGFR", "uniprot": "P00533", "chemblId": "CHEMBL203" },
    "approvedDrugs": [
      { "name": "Erlotinib", "chemblId": "CHEMBL553", "smiles": "C#Cc1cccc(...)c1", "mechanism": "Inhibitor" },
      { "name": "Gefitinib", "chemblId": "CHEMBL939", "smiles": "...", "mechanism": "Inhibitor" }
    ],
    "potentCompounds": {
      "count": 3737,
      "minPchemblFilter": 6.0,
      "topHits": [
        { "chemblId": "CHEMBL68920", "smiles": "...", "pchembl": 7.39, "assayType": "IC50" }
      ]
    }
  }
}
```

---

## 9. Visualizer Integration Notes

### CORS-verified endpoints (all return `Access-Control-Allow-Origin: *`)

| Endpoint | Verified |
|----------|----------|
| `files.rcsb.org` | Yes |
| `models.rcsb.org` | Yes |
| `alphafold.ebi.ac.uk/api/` | Yes |
| `alphafold.ebi.ac.uk/files/` | Yes (via preflight) |
| `www.ebi.ac.uk/pdbe/` | Yes |
| `rest.uniprot.org` | Yes |
| `pubchem.ncbi.nlm.nih.gov/rest/pug/` | Yes |
| `www.ebi.ac.uk/chembl/api/` | Yes |

No proxy needed. All work directly from browser `fetch()`.

### Recommended viewer libraries

| Library | Best for | Bundle size | Format preference |
|---------|----------|------------|-------------------|
| **Mol*** (molstar) | Large structures, production use | ~2MB | BinaryCIF |
| **3Dmol.js** | Quick integration, small structures | ~500KB | PDB/CIF |

### Mol* embedding

```
https://molstar.org/viewer/?pdb=4HHB
https://molstar.org/viewer/?afdb=Q8W3K0
https://molstar.org/viewer/?structure-url=https://example.com/file.cif&structure-url-format=mmcif
```

### 3Dmol.js loading

```javascript
// By PDB ID (auto-fetches from RCSB)
$3Dmol.download('pdb:4HHB', viewer, {}, function(model) {
  viewer.setStyle({}, { cartoon: { color: 'spectrum' } });
  viewer.render();
});

// Manual fetch for more control
const data = await fetch('https://files.rcsb.org/download/4HHB.cif').then(r => r.text());
viewer.addModel(data, 'cif');
```

### Priority order for fetching structures in the visualizer

1. **RCSB BinaryCIF** (`models.rcsb.org/{PDBID}.bcif`) — smallest, fastest
2. **PDBe BinaryCIF** — European fallback
3. **AlphaFold BinaryCIF** — predicted structures
4. **RCSB text CIF** — fallback
5. **ESMFold POST** — real-time prediction from sequence

### Geographic routing

Consider routing to the nearest mirror:

| User region | Primary | Fallback |
|------------|---------|----------|
| Americas | RCSB (`rcsb.org`) | PDBe (`ebi.ac.uk`) |
| Europe/Africa | PDBe (`ebi.ac.uk`) | RCSB |
| Asia-Pacific | PDBj (`pdbj.org`) | RCSB |

---

## 10. Quick Reference Table

### Protein resolution

| I have... | I need... | API call |
|-----------|-----------|----------|
| Gene name + organism | UniProt accession | `rest.uniprot.org/uniprotkb/search?query=(gene:{GENE})+AND+(organism_id:{ID})+AND+(reviewed:true)` |
| UniProt accession | Best PDB structures | `ebi.ac.uk/pdbe/graph-api/mappings/best_structures/{UNIPROT}` |
| UniProt accession | AlphaFold structure | `alphafold.ebi.ac.uk/api/prediction/{UNIPROT}` |
| PDB ID | Download CIF | `files.rcsb.org/download/{PDBID}.cif` |
| PDB ID | Download BinaryCIF | `models.rcsb.org/{PDBID}.bcif` |
| PDB ID | UniProt mapping | `ebi.ac.uk/pdbe/api/mappings/uniprot/{PDBID}` |
| Amino acid sequence | Predicted structure | `POST api.esmatlas.com/foldSequence/v1/pdb/` |

### Ligand resolution

| I have... | I need... | API call |
|-----------|-----------|----------|
| Drug/compound name | 3D SDF | `pubchem.ncbi.nlm.nih.gov/rest/pug/compound/name/{NAME}/record/SDF?record_type=3d` |
| Drug/compound name | SMILES + properties | `pubchem.ncbi.nlm.nih.gov/rest/pug/compound/name/{NAME}/property/IsomericSMILES,MolecularWeight/JSON` |
| SMILES string | 3D SDF | RDKit locally: `EmbedMolecule` + `MMFFOptimizeMolecule` |
| CCD 3-letter code | Ideal SDF | `files.rcsb.org/ligands/download/{CCD}_ideal.sdf` |
| PDB ID + CCD code | Experimental pose SDF | `models.rcsb.org/v1/{PDBID}/ligand?label_comp_id={CCD}&encoding=sdf` |
| ChEMBL ID | SDF | `ebi.ac.uk/chembl/api/data/molecule/{CHEMBL_ID}?format=sdf` |
| ChEMBL ID | SMILES + metadata | `ebi.ac.uk/chembl/api/data/molecule/{CHEMBL_ID}.json` |
| PubChem CID | 3D SDF | `pubchem.ncbi.nlm.nih.gov/rest/pug/compound/cid/{CID}/record/SDF?record_type=3d` |

### Target → binder discovery

| I have... | I need... | API call |
|-----------|-----------|----------|
| UniProt accession | ChEMBL target ID | `ebi.ac.uk/chembl/api/data/target.json?target_components__accession={UNIPROT}` |
| ChEMBL target ID | Active compounds | `ebi.ac.uk/chembl/api/data/activity.json?target_chembl_id={TARGET}&pchembl_value__gte=6` |
| ChEMBL target ID | Approved drugs | `ebi.ac.uk/chembl/api/data/mechanism.json?target_chembl_id={TARGET}` |
