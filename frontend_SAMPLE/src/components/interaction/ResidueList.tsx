interface ResidueListProps {
  residues: string[];
}

export default function ResidueList({ residues }: ResidueListProps) {
  return (
    <div className="flex flex-wrap gap-2">
      {residues.map((r) => (
        <span
          key={r}
          className="px-3 py-1.5 text-sm rounded-lg bg-teal-50 text-teal-700 border border-teal-200 font-mono"
        >
          {r}
        </span>
      ))}
    </div>
  );
}
