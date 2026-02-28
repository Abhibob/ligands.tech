import type { FileEntry } from '../types/index.ts';
import { generateFileId } from '../state/store.ts';

export async function fetchFromPubChem(nameOrCid: string): Promise<FileEntry> {
  const query = nameOrCid.trim();
  let cid: string;

  // If it's a number, use as CID directly
  if (/^\d+$/.test(query)) {
    cid = query;
  } else {
    // Resolve name to CID
    const searchUrl = `https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/name/${encodeURIComponent(query)}/cids/JSON`;
    const searchResp = await fetch(searchUrl);
    if (!searchResp.ok) throw new Error(`Compound "${query}" not found on PubChem`);
    const searchData = await searchResp.json();
    cid = String(searchData.IdentifierList.CID[0]);
  }

  // Fetch 3D SDF
  const sdfUrl = `https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/cid/${cid}/record/SDF?record_type=3d`;
  const resp = await fetch(sdfUrl);
  if (!resp.ok) throw new Error(`3D structure not available for CID ${cid}`);
  const content = await resp.text();

  return {
    id: generateFileId(),
    name: `${query}_CID${cid}.sdf`,
    format: 'sdf',
    content,
    source: 'pubchem',
  };
}
