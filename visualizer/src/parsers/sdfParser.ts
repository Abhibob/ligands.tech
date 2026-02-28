import type { GninaPose } from '../types/gnina.ts';

// Split multi-model SDF on $$$$ and extract gnina SD properties per pose
export function parseMultiModelSdf(sdfText: string): GninaPose[] {
  const blocks = sdfText.split('$$$$').filter(b => b.trim().length > 0);

  return blocks.map((block, index) => ({
    index,
    minimizedAffinity: extractSdProperty(block, 'minimizedAffinity'),
    cnnScore: extractSdProperty(block, 'CNNscore'),
    cnnAffinity: extractSdProperty(block, 'CNNaffinity'),
    cnnVS: extractSdProperty(block, 'CNN_VS'),
    sdfBlock: block.trim() + '\n$$$$',
  }));
}

function extractSdProperty(block: string, propertyName: string): number | null {
  // SD property format: >  <propertyName>\nvalue\n
  const regex = new RegExp(`>\\s*<${propertyName}>\\s*\\n\\s*([^\\n]+)`, 'i');
  const match = block.match(regex);
  if (!match) return null;
  const val = parseFloat(match[1].trim());
  return isNaN(val) ? null : val;
}

export function isMultiModelSdf(sdfText: string): boolean {
  return (sdfText.match(/\$\$\$\$/g) ?? []).length > 1;
}
