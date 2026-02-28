import { useStore } from '../../state/store.ts';

export default function LigandPropertiesCard() {
  const props = useStore((s) => s.ligandProperties);

  if (!props) return null;

  return (
    <div>
      <h3 className="text-sm font-semibold text-gray-700 mb-2">Ligand Properties</h3>
      <div className="space-y-1.5">
        <div className="text-sm font-medium text-gray-900">{props.name}</div>
        <div className="text-xs text-gray-500">
          CID:{' '}
          <a
            href={`https://pubchem.ncbi.nlm.nih.gov/compound/${props.cid}`}
            target="_blank"
            rel="noopener noreferrer"
            className="text-blue-600 hover:underline"
          >
            {props.cid}
          </a>
        </div>

        <div className="flex flex-wrap gap-x-3 gap-y-0.5 text-xs text-gray-600">
          <span>
            Formula: <span className="font-medium">{props.formula}</span>
          </span>
          <span>
            MW: <span className="font-medium">{props.molecularWeight.toFixed(1)}</span>
          </span>
        </div>

        {props.smiles && (
          <div className="text-xs text-gray-400 break-all font-mono leading-tight">
            {props.smiles}
          </div>
        )}

        <div className="flex flex-wrap gap-1.5 mt-1">
          {props.xLogP != null && (
            <PropertyBadge label="LogP" value={props.xLogP.toFixed(1)} />
          )}
          {props.tpsa != null && (
            <PropertyBadge label="TPSA" value={props.tpsa.toFixed(0)} />
          )}
          {props.hBondDonors != null && (
            <PropertyBadge label="HBD" value={String(props.hBondDonors)} />
          )}
          {props.hBondAcceptors != null && (
            <PropertyBadge label="HBA" value={String(props.hBondAcceptors)} />
          )}
        </div>
      </div>
    </div>
  );
}

function PropertyBadge({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-center gap-1 rounded-full border border-gray-200 px-2 py-0.5">
      <span className="text-xs text-gray-500">{label}</span>
      <span className="text-xs font-bold text-gray-700">{value}</span>
    </div>
  );
}
