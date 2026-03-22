const STORAGE_KEY = 'hive.capability.llmModelHistory';
const MAX = 24;

function readRaw(): string[] {
  if (typeof window === 'undefined') return [];
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return [];
    const arr = JSON.parse(raw);
    return Array.isArray(arr) ? arr.filter((x) => typeof x === 'string' && x.trim()) : [];
  } catch {
    return [];
  }
}

export function getLlmModelHistory(): string[] {
  return readRaw();
}

/** Remember a model id after a successful save (deduped, newest first). */
export function rememberLlmModel(model: string): void {
  const m = model.trim();
  if (!m || typeof window === 'undefined') return;
  const prev = readRaw().filter((x) => x.toLowerCase() !== m.toLowerCase());
  const next = [m, ...prev].slice(0, MAX);
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(next));
  } catch {
    /* ignore quota */
  }
}
