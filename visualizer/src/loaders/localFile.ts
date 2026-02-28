import type { FileEntry } from '../types/index.ts';
import { detectFormat } from '../parsers/fileDetect.ts';
import { generateFileId } from '../state/store.ts';

export async function loadLocalFile(file: File): Promise<FileEntry> {
  const content = await file.text();
  const format = detectFormat(file.name, content);

  return {
    id: generateFileId(),
    name: file.name,
    format,
    content,
    source: 'local',
  };
}
