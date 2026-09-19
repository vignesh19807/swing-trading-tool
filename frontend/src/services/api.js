/**
 * API Service Layer
 *
 * All backend communication flows through this module.
 * Components and pages must never call fetch/axios directly —
 * they should import and use functions from this file.
 *
 * Architecture:
 *   React UI → src/services/api.js → Backend API → Backend Logic → Database
 *
 * Environment variable:
 *   VITE_API_BASE_URL — set in .env (see .env.example for reference)
 *
 * NOTE: This file is intentionally minimal for Phase 1.
 *       Backend endpoints are not yet connected. Expand this in Phase 2+.
 */

const BASE_URL = import.meta.env.VITE_API_BASE_URL ?? '';

/**
 * Generic fetch wrapper.
 * @param {string} path  - API path relative to BASE_URL (e.g. "/api/stocks")
 * @param {RequestInit} [options] - Optional fetch options
 * @returns {Promise<any>}
 */
async function apiFetch(path, options = {}) {
  const url = `${BASE_URL}${path}`;
  const response = await fetch(url, {
    headers: {
      'Content-Type': 'application/json',
      ...options.headers,
    },
    ...options,
  });

  if (!response.ok) {
    throw new Error(`API error ${response.status}: ${response.statusText} (${url})`);
  }

  return response.json();
}

// ---------------------------------------------------------------------------
// Future endpoint stubs — implement in Phase 2+
// ---------------------------------------------------------------------------

// export const getDashboard = () => apiFetch('/api/dashboard');
// export const getStockDetail = (symbol) => apiFetch(`/api/stocks/${symbol}`);
// export const getSectors = () => apiFetch('/api/sectors');
// export const getWatchlist = () => apiFetch('/api/watchlist');
// export const getPerformance = () => apiFetch('/api/performance');

export { apiFetch };
