import type { Story } from './api';

export interface SavedStory { id: number; title: string; created_at: string; nodeCount: number }
const prefix = 'fable:v1:';

function read(key: string): unknown {
  try { return JSON.parse(localStorage.getItem(prefix + key) || 'null'); }
  catch { return null; }
}
function write(key: string, value: unknown) {
  try { localStorage.setItem(prefix + key, JSON.stringify(value)); }
  catch { /* Reading and creating stories still works if storage is unavailable. */ }
}

export function library(): SavedStory[] {
  const items = read('library');
  if (!Array.isArray(items)) return [];
  return items.filter((item): item is SavedStory => item && Number.isInteger(item.id)
    && item.id > 0 && typeof item.title === 'string' && typeof item.created_at === 'string'
    && Number.isInteger(item.nodeCount));
}
export function remember(story: Story) {
  const saved = { id: story.id, title: story.title, created_at: story.created_at, nodeCount: Object.keys(story.all_nodes).length };
  write('library', [saved, ...library().filter(item => item.id !== story.id)].slice(0, 40));
}
export function draft(): string { const value = read('draft'); return typeof value === 'string' ? value : ''; }
export function saveDraft(value: string) { write('draft', value); }
export function draftLanguage(): string { return read('language') === 'Arabic' ? 'Arabic' : 'English'; }
export function saveLanguage(value: string) { write('language', value); }
export function activeJob(): string | null { const value = read('job'); return typeof value === 'string' ? value : null; }
export function saveJob(id: string) { write('job', id); }
export function clearJob(id: string) { if (activeJob() === id) write('job', null); }
export function savePath(id: number, path: number[]) { write(`path:${id}`, path); }
export function storyPath(story: Story): number[] {
  const saved = read(`path:${story.id}`);
  const path = [story.root_node.id];
  if (!Array.isArray(saved) || saved[0] !== story.root_node.id) return path;
  for (const id of saved.slice(1)) {
    const previous = story.all_nodes[String(path[path.length - 1])];
    if (!Number.isInteger(id) || !story.all_nodes[String(id)] || !previous
      || previous.is_ending || !previous.options.some(option => option.node_id === id)) break;
    if (path.includes(id)) break;
    path.push(id);
  }
  return path;
}
