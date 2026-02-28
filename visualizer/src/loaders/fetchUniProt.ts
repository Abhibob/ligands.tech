import type { FileEntry } from '../types/index.ts';
import type { ProteinResolution, PdbStructure } from '../types/resolution.ts';
import { generateFileId } from '../state/store.ts';

interface UniProtResult {
  primaryAccession: string;
  proteinDescription?: {
    recommendedName?: { fullName?: { value?: string } };
    submittedName?: Array<{ fullName?: { value?: string } }>;
  };
  genes?: Array<{
    geneName?: { value?: string };
    synonyms?: Array<{ value?: string }>;
  }>;
  organism?: { scientificName?: string };
  sequence?: { length?: number };
}

interface PdbeStructure {
  pdb_id: string;
  chain_id: string;
  experimental_method: string;
  resolution: number | null;
  coverage: number;
  unp_start: number;
  unp_end: number;
}

/**
 * Resolve a protein name/gene to a UniProt accession, then find the best
 * experimental PDB structures. Returns both the resolution metadata and
 * the downloaded FileEntry for the best structure.
 */
export async function resolveProteinName(
  name: string,
): Promise<{ resolution: ProteinResolution; entry: FileEntry }> {
  const query = name.trim();

  // Step 1: UniProt Search API → accession
  const searchUrl =
    `https://rest.uniprot.org/uniprotkb/search?` +
    `query=(gene:${encodeURIComponent(query)})+AND+(organism_id:9606)+AND+(reviewed:true)` +
    `&fields=accession,gene_names,protein_name,organism_name,sequence` +
    `&format=json&size=1`;

  const searchResp = await fetch(searchUrl);
  if (!searchResp.ok) throw new Error(`UniProt search failed for "${query}"`);
  const searchData = await searchResp.json();

  const results: UniProtResult[] = searchData.results ?? [];
  if (results.length === 0) {
    throw new Error(`No reviewed human protein found for "${query}"`);
  }

  const hit = results[0];
  const accession = hit.primaryAccession;
  const proteinName =
    hit.proteinDescription?.recommendedName?.fullName?.value ??
    hit.proteinDescription?.submittedName?.[0]?.fullName?.value ??
    query;
  const gene = hit.genes?.[0]?.geneName?.value ?? query;
  const synonyms =
    hit.genes?.[0]?.synonyms?.map((s) => s.value).filter(Boolean) as string[] ?? [];
  const organism = hit.organism?.scientificName ?? 'Homo sapiens';
  const sequenceLength = hit.sequence?.length ?? 0;

  // Step 2: PDBe Best Structures API → ranked PDB list
  let bestStructures: PdbStructure[] = [];
  let alphafoldAvailable = false;

  try {
    const pdbeUrl = `https://www.ebi.ac.uk/pdbe/graph-api/mappings/best_structures/${accession}`;
    const pdbeResp = await fetch(pdbeUrl);
    if (pdbeResp.ok) {
      const pdbeData = await pdbeResp.json();
      const structs: PdbeStructure[] = pdbeData[accession] ?? [];
      bestStructures = structs.slice(0, 10).map((s) => ({
        pdbId: s.pdb_id.toUpperCase(),
        chainId: s.chain_id,
        method: s.experimental_method,
        resolution: s.resolution,
        coverage: s.coverage,
        unpStart: s.unp_start,
        unpEnd: s.unp_end,
      }));
    }
  } catch {
    /* PDBe unavailable — will use AlphaFold fallback */
  }

  // Check AlphaFold availability
  try {
    const afResp = await fetch(`https://alphafold.ebi.ac.uk/api/prediction/${accession}`);
    alphafoldAvailable = afResp.ok;
  } catch {
    alphafoldAvailable = false;
  }

  const resolution: ProteinResolution = {
    accession,
    name: proteinName,
    gene,
    synonyms,
    organism,
    sequenceLength,
    bestStructures,
    alphafoldAvailable,
  };

  // Step 3: Download the best structure
  let entry: FileEntry;

  if (bestStructures.length > 0) {
    const best = bestStructures[0];
    entry = await downloadPdbStructure(best.pdbId);
  } else if (alphafoldAvailable) {
    // AlphaFold fallback
    const cifUrl = `https://alphafold.ebi.ac.uk/files/AF-${accession}-F1-model_v4.cif`;
    const resp = await fetch(cifUrl);
    if (!resp.ok) throw new Error(`Failed to download AlphaFold structure for ${accession}`);
    const content = await resp.text();
    entry = {
      id: generateFileId(),
      name: `AF-${accession}.cif`,
      format: 'mmcif',
      content,
      source: 'alphafold',
    };
  } else {
    throw new Error(`No structures found for "${query}" (${accession})`);
  }

  return { resolution, entry };
}

/**
 * Download a PDB structure by ID (BinaryCIF first, fallback to text CIF).
 */
export async function downloadPdbStructure(pdbId: string): Promise<FileEntry> {
  const id = pdbId.toUpperCase().trim();
  const bcifUrl = `https://models.rcsb.org/${id}.bcif`;

  try {
    const resp = await fetch(bcifUrl);
    if (resp.ok) {
      const buffer = await resp.arrayBuffer();
      return {
        id: generateFileId(),
        name: `${id}.bcif`,
        format: 'bcif',
        content: buffer,
        source: 'rcsb',
      };
    }
  } catch { /* fallback */ }

  const cifUrl = `https://files.rcsb.org/download/${id}.cif`;
  const resp = await fetch(cifUrl);
  if (!resp.ok) throw new Error(`PDB ID "${id}" not found on RCSB`);
  const content = await resp.text();

  return {
    id: generateFileId(),
    name: `${id}.cif`,
    format: 'mmcif',
    content,
    source: 'rcsb',
  };
}
