/**
 * LocalStorage history utility for TruthLens
 */

const HISTORY_KEY = 'truthlens_history_v1';
const MAX_HISTORY_ITEMS = 30;

export function getHistory() {
  try {
    const raw = localStorage.getItem(HISTORY_KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw);
    return Array.isArray(parsed) ? parsed : [];
  } catch (err) {
    console.error('Failed to read TruthLens history from localStorage:', err);
    return [];
  }
}

export function saveAnalysisToHistory(normalized, rawResponse) {
  try {
    if (!normalized || !normalized.source?.url) return;

    const history = getHistory();
    const id = `tl_${Date.now()}_${Math.random().toString(36).substring(2, 7)}`;

    const newItem = {
      id,
      url: normalized.source.url,
      platform: normalized.source.platform || 'unknown',
      author: normalized.author?.name || normalized.author?.username || 'Unknown',
      authorUsername: normalized.author?.username || '',
      verdict: normalized.overall.verdict.label,
      rawVerdict: normalized.overall.rawVerdict,
      badgeClass: normalized.overall.verdict.badgeClass,
      timestamp: new Date().toISOString(),
      claimsCount: normalized.overall.claimsDetected,
      fullResponse: rawResponse,
    };

    // Deduplicate by URL: remove older entry for same URL if exists
    const filtered = history.filter((item) => item.url !== newItem.url);
    const updated = [newItem, ...filtered].slice(0, MAX_HISTORY_ITEMS);

    localStorage.setItem(HISTORY_KEY, JSON.stringify(updated));
    return newItem;
  } catch (err) {
    console.error('Failed to save TruthLens history to localStorage:', err);
    return null;
  }
}

export function clearHistory() {
  try {
    localStorage.removeItem(HISTORY_KEY);
  } catch (err) {
    console.error('Failed to clear TruthLens history:', err);
  }
}

export function getHistoryItemById(id) {
  const history = getHistory();
  return history.find((item) => item.id === id) || null;
}
