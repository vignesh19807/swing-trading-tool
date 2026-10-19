/**
 * @file watchlistStorage.js
 * @description Pure utility functions for managing local watchlist persistence,
 * performance tracking, filtering, and sorting.
 *
 * SPECIFICATION:
 *   - LocalStorage persistence under 'swing-trading-watchlist'
 *   - Safe normalization for legacy formats (string arrays) and corrupted data
 *   - Prevents duplicate entries with case-insensitive symbol comparison
 *   - Performance since added calculation: ((currentPrice - addedPrice) / addedPrice) * 100
 *   - Pure functions with no React dependencies
 */

export const WATCHLIST_STORAGE_KEY = 'swing-trading-watchlist';

/**
 * Normalizes an individual watchlist item into a consistent schema.
 *
 * @param {string|object} item
 * @returns {object|null} Normalized watchlist item or null if invalid
 */
export function normalizeWatchlistItem(item) {
  if (!item) return null;

  if (typeof item === 'string') {
    const cleanSym = item.trim().toUpperCase().replace(/[^A-Z0-9-]/g, '');
    if (!cleanSym) return null;
    return {
      symbol: cleanSym,
      company_name: '',
      sector: '',
      addedAt: new Date().toISOString(),
      addedPrice: null,
      notes: '',
    };
  }

  if (typeof item === 'object') {
    const rawSym = item.symbol || item.ticker || '';
    const cleanSym = String(rawSym).trim().toUpperCase().replace(/[^A-Z0-9-]/g, '');
    if (!cleanSym) return null;

    const addedPrice = item.addedPrice != null && !isNaN(Number(item.addedPrice)) && Number(item.addedPrice) > 0
      ? Number(item.addedPrice)
      : (item.current_price != null && !isNaN(Number(item.current_price)) && Number(item.current_price) > 0
        ? Number(item.current_price)
        : null);

    return {
      symbol: cleanSym,
      company_name: item.company_name || item.companyName || '',
      sector: item.sector || '',
      addedAt: item.addedAt || new Date().toISOString(),
      addedPrice,
      notes: typeof item.notes === 'string' ? item.notes : '',
    };
  }

  return null;
}

/**
 * Loads and normalizes the watchlist from localStorage.
 *
 * @param {Storage} [storage=window.localStorage]
 * @returns {Array<object>} Array of valid watchlist items
 */
export function loadWatchlist(storage = (typeof window !== 'undefined' ? window.localStorage : null)) {
  if (!storage) return [];

  try {
    const raw = storage.getItem(WATCHLIST_STORAGE_KEY);
    if (!raw) return [];

    const parsed = JSON.parse(raw);
    if (!Array.isArray(parsed)) return [];

    const seen = new Set();
    const result = [];

    for (const entry of parsed) {
      const normalized = normalizeWatchlistItem(entry);
      if (normalized && !seen.has(normalized.symbol)) {
        seen.add(normalized.symbol);
        result.push(normalized);
      }
    }

    return result;
  } catch (err) {
    console.error('Failed to parse watchlist from localStorage:', err);
    return [];
  }
}

/**
 * Saves a list of watchlist items to localStorage.
 *
 * @param {Array<object>} items
 * @param {Storage} [storage=window.localStorage]
 * @returns {boolean} True if successfully saved
 */
export function saveWatchlist(items, storage = (typeof window !== 'undefined' ? window.localStorage : null)) {
  if (!storage) return false;

  try {
    const validItems = Array.isArray(items)
      ? items.map(normalizeWatchlistItem).filter(Boolean)
      : [];
    storage.setItem(WATCHLIST_STORAGE_KEY, JSON.stringify(validItems));
    return true;
  } catch (err) {
    console.error('Failed to save watchlist to localStorage:', err);
    return false;
  }
}

/**
 * Adds a stock to the watchlist.
 * Prevents duplicate entries and captures current price as addedPrice if available.
 *
 * @param {Array<object>} currentList
 * @param {string|object} stockOrSymbol
 * @returns {{ success: boolean, list: Array<object>, item: object|null, isDuplicate: boolean, error?: string }}
 */
export function addStockToWatchlist(currentList = [], stockOrSymbol) {
  const normalized = normalizeWatchlistItem(stockOrSymbol);
  if (!normalized || !normalized.symbol) {
    return {
      success: false,
      list: currentList,
      item: null,
      isDuplicate: false,
      error: 'Invalid stock symbol or data provided.',
    };
  }

  const list = Array.isArray(currentList) ? currentList : [];
  const exists = list.some((item) => (item.symbol || '').toUpperCase() === normalized.symbol);

  if (exists) {
    return {
      success: false,
      list,
      item: normalized,
      isDuplicate: true,
      error: `${normalized.symbol} is already in your watchlist.`,
    };
  }

  const updatedList = [normalized, ...list];
  return {
    success: true,
    list: updatedList,
    item: normalized,
    isDuplicate: false,
  };
}

/**
 * Removes a stock from the watchlist.
 *
 * @param {Array<object>} currentList
 * @param {string} symbol
 * @returns {{ success: boolean, list: Array<object>, removedItem: object|null }}
 */
export function removeStockFromWatchlist(currentList = [], symbol) {
  if (!symbol) {
    return { success: false, list: currentList, removedItem: null };
  }

  const targetSymbol = String(symbol).trim().toUpperCase();
  const list = Array.isArray(currentList) ? currentList : [];

  const removedItem = list.find((item) => (item.symbol || '').toUpperCase() === targetSymbol) || null;
  const updatedList = list.filter((item) => (item.symbol || '').toUpperCase() !== targetSymbol);

  return {
    success: Boolean(removedItem),
    list: updatedList,
    removedItem,
  };
}

/**
 * Computes performance since a stock was added to the watchlist.
 * Formula: ((currentPrice - addedPrice) / addedPrice) * 100
 *
 * @param {number|null|undefined} currentPrice
 * @param {number|null|undefined} addedPrice
 * @returns {number|null} Percentage change or null if either price is missing/invalid
 */
export function calculatePerformanceSinceAdded(currentPrice, addedPrice) {
  if (
    currentPrice == null ||
    isNaN(Number(currentPrice)) ||
    Number(currentPrice) <= 0 ||
    addedPrice == null ||
    isNaN(Number(addedPrice)) ||
    Number(addedPrice) <= 0
  ) {
    return null;
  }

  const curr = Number(currentPrice);
  const baseline = Number(addedPrice);
  return ((curr - baseline) / baseline) * 100;
}

/**
 * Filters a combined watchlist (watchlist items merged with live stock universe data).
 *
 * @param {Array<object>} items - Merged watchlist stock records
 * @param {object} options
 * @param {string} [options.search=''] - Search term for symbol or company name
 * @param {string} [options.filter='ALL'] - 'ALL' | 'GAINERS' | 'DECLINERS'
 * @returns {Array<object>} Filtered items
 */
export function filterWatchlist(items = [], { search = '', filter = 'ALL' } = {}) {
  if (!Array.isArray(items)) return [];

  const query = (search || '').trim().toLowerCase();

  return items.filter((item) => {
    // 1. Search Query Filter (Symbol or Company Name)
    if (query) {
      const symMatch = (item.symbol || '').toLowerCase().includes(query);
      const nameMatch = (item.company_name || item.companyName || '').toLowerCase().includes(query);
      if (!symMatch && !nameMatch) return false;
    }

    // 2. Gainers / Decliners Filter
    if (filter && filter !== 'ALL') {
      const change = item.change_percent ?? item.price_change_percent;
      const numChange = change != null && !isNaN(Number(change)) ? Number(change) : null;

      if (filter === 'GAINERS') {
        if (numChange == null || numChange <= 0) return false;
      } else if (filter === 'DECLINERS') {
        if (numChange == null || numChange >= 0) return false;
      }
    }

    return true;
  });
}

/**
 * Sorts a merged watchlist array.
 *
 * Supported sort keys:
 *   - 'symbol-asc' / 'symbol-desc'
 *   - 'price-desc' / 'price-asc'
 *   - 'change-desc' / 'change-asc' (Daily change)
 *   - 'perf-desc' / 'perf-asc' (Performance since added)
 *   - 'added-desc' / 'added-asc' (Added date)
 *   - 'score-desc' / 'score-asc' (Opportunity score)
 *
 * @param {Array<object>} items - Merged watchlist items
 * @param {string} [sortBy='symbol-asc']
 * @returns {Array<object>} Sorted shallow copy
 */
export function sortWatchlist(items = [], sortBy = 'symbol-asc') {
  if (!Array.isArray(items)) return [];

  const copy = [...items];

  return copy.sort((a, b) => {
    const symA = a.symbol || '';
    const symB = b.symbol || '';

    const priceA = a.current_price ?? a.currentPrice ?? a.price ?? 0;
    const priceB = b.current_price ?? b.currentPrice ?? b.price ?? 0;

    const changeA = a.change_percent ?? a.price_change_percent ?? 0;
    const changeB = b.change_percent ?? b.price_change_percent ?? 0;

    const perfA = a.perfSinceAdded ?? (calculatePerformanceSinceAdded(priceA, a.addedPrice) ?? -Infinity);
    const perfB = b.perfSinceAdded ?? (calculatePerformanceSinceAdded(priceB, b.addedPrice) ?? -Infinity);

    const dateA = a.addedAt ? new Date(a.addedAt).getTime() : 0;
    const dateB = b.addedAt ? new Date(b.addedAt).getTime() : 0;

    const scoreA = a.opportunity_score ?? 0;
    const scoreB = b.opportunity_score ?? 0;

    switch (sortBy) {
      case 'symbol-asc':
        return symA.localeCompare(symB);
      case 'symbol-desc':
        return symB.localeCompare(symA);

      case 'price-desc':
        return Number(priceB) - Number(priceA);
      case 'price-asc':
        return Number(priceA) - Number(priceB);

      case 'change-desc':
        return Number(changeB) - Number(changeA);
      case 'change-asc':
        return Number(changeA) - Number(changeB);

      case 'perf-desc':
        return Number(perfB) - Number(perfA);
      case 'perf-asc':
        return Number(perfA) - Number(perfB);

      case 'added-desc':
        return dateB - dateA;
      case 'added-asc':
        return dateA - dateB;

      case 'score-desc':
        return Number(scoreB) - Number(scoreA);
      case 'score-asc':
        return Number(scoreA) - Number(scoreB);

      default:
        return symA.localeCompare(symB);
    }
  });
}
