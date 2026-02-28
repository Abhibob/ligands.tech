import type { LigandProperties } from '../types/resolution.ts';

/**
 * Fetch molecular properties from PubChem for a compound name or CID.
 */
export async function fetchLigandProperties(
  nameOrCid: string,
): Promise<LigandProperties> {
  const query = nameOrCid.trim();
  const isNumeric = /^\d+$/.test(query);
  const idType = isNumeric ? 'cid' : 'name';

  const propsUrl =
    `https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/${idType}/` +
    `${encodeURIComponent(query)}/property/` +
    `IUPACName,MolecularFormula,MolecularWeight,IsomericSMILES,XLogP,TPSA,HBondDonorCount,HBondAcceptorCount` +
    `/JSON`;

  const resp = await fetch(propsUrl);
  if (!resp.ok) throw new Error(`PubChem properties not found for "${query}"`);
  const data = await resp.json();

  const props = data.PropertyTable?.Properties?.[0];
  if (!props) throw new Error(`No properties returned for "${query}"`);

  return {
    name: props.IUPACName ?? query,
    cid: props.CID,
    formula: props.MolecularFormula ?? '',
    molecularWeight: parseFloat(props.MolecularWeight) || 0,
    smiles: props.IsomericSMILES ?? '',
    xLogP: props.XLogP ?? null,
    tpsa: props.TPSA ?? null,
    hBondDonors: props.HBondDonorCount ?? null,
    hBondAcceptors: props.HBondAcceptorCount ?? null,
  };
}
