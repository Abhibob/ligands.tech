import ProteinCard from '../resolution/ProteinCard.tsx';
import LigandPropertiesCard from '../resolution/LigandPropertiesCard.tsx';
import PoseTable from '../gnina/PoseTable.tsx';
import ConfidenceBadges from '../boltz/ConfidenceBadges.tsx';
import AffinityCard from '../boltz/AffinityCard.tsx';
import InteractionOverlay from '../plip/InteractionOverlay.tsx';
import InteractionTable from '../plip/InteractionTable.tsx';

export default function InfoPanel() {
  return (
    <div className="h-full bg-white border-l border-gray-200 overflow-y-auto p-3 space-y-4">
      <ProteinCard />
      <LigandPropertiesCard />
      <ConfidenceBadges />
      <AffinityCard />
      <PoseTable />
      <InteractionOverlay />
      <InteractionTable />
    </div>
  );
}
