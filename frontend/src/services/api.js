/**
 * @file api.js
 * @description Central API service layer for the Swing Trading Intelligence Platform.
 *
 * ARCHITECTURE RULE:
 *   All HTTP requests MUST go through this module.
 *   Components and pages must NOT call fetch() directly.
 *
 * DATA FLOW:
 *   React UI → this service → Backend REST API → Backend Logic/Data → Database
 *
 * ENVIRONMENT:
 *   VITE_API_BASE_URL — set in .env.local (see .env.example)
 *   VITE_USE_MOCK_DATA — set to "true" only during offline/test development
 *
 * Phase 1 NOTE:
 *   Function bodies return null placeholders until the backend API layer is
 *   ready. Do NOT add real fetch() calls here until Phase 3 integration.
 */

// ---------------------------------------------------------------------------
// Configuration
// ---------------------------------------------------------------------------

const BASE_URL = import.meta.env.VITE_API_BASE_URL; 
const USE_MOCK = import.meta.env.VITE_USE_MOCK_DATA === "true";

/**
 * Internal fetch wrapper.
 * Centralises error handling, JSON parsing, and future auth-header injection.
 *
 * @param {string} path  - API path (e.g. "/api/opportunities")
 * @param {RequestInit} [options] - Standard fetch options
 * @returns {Promise<any>} Parsed JSON response
 */
async function request(path, options = {}) {
  if (!USE_MOCK && !BASE_URL) {
    throw new Error("Configuration Error: VITE_API_BASE_URL is missing. Real API mode requires this environment variable.");
  }

  const url = `${BASE_URL || ''}${path}`;

  let response;
  try {
    response = await fetch(url, {
      headers: {
        "Content-Type": "application/json",
        // Future: Authorization: `Bearer ${token}`
        ...options.headers,
      },
      ...options,
    });
  } catch (err) {
    throw new Error(`Network Error: Failed to reach the API. ${err.message}`);
  }

  if (!response.ok) {
    const error = new Error(`API error: ${response.status} ${response.statusText}`);
    error.status = response.status;
    throw error;
  }

  return response.json();
}

// ---------------------------------------------------------------------------
// Planned API Endpoints (Phase 3 integration targets)
// These functions define the contract between the frontend and backend.
// Return values are null until backend routes are implemented.
// ---------------------------------------------------------------------------

/**
 * GET /api/opportunities
 * Returns ranked swing opportunities for the current universe.
 */
export async function getOpportunities() {
  if (USE_MOCK) {
    const { mockOpportunities } = await import("../data/mockOpportunities.js");
    return mockOpportunities;
  }
  return request("/api/opportunities");
}

/**
 * GET /api/stocks
 * Returns the full list of stocks in the universe.
 */
export async function getStocks() {
  if (USE_MOCK) {
    const { mockStocks } = await import("../data/mockStocks.js");
    return mockStocks;
  }
  return request("/api/stocks");
}

/**
 * GET /api/stocks/:symbol
 * Returns full intelligence report for a single stock.
 *
 * @param {string} symbol - NSE ticker symbol (e.g. "TCS")
 */
export async function getStock(symbol) {
  if (USE_MOCK) {
    const { mockStock } = await import("../data/mockStock.js");
    return mockStock;
  }
  return request(`/api/stocks/${encodeURIComponent(symbol)}`);
}

/**
 * GET /api/stocks/:symbol/history
 * Returns historical OHLCV data for charting.
 *
 * @param {string} symbol - NSE ticker symbol
 */
export async function getStockHistory(symbol) {
  if (USE_MOCK) {
    const { mockStockHistory } = await import("../data/mockHistory.js");
    return mockStockHistory;
  }
  return request(`/api/stocks/${encodeURIComponent(symbol)}/history`);
}

/**
 * GET /api/sectors
 * Returns sector and industry performance summary.
 */
export async function getSectors() {
  if (USE_MOCK) {
    const { mockSectors } = await import("../data/mockSectors.js");
    return mockSectors;
  }
  return request("/api/sectors");
}

/**
 * GET /api/market/indices
 * Returns current market index data (NIFTY 50, etc.).
 */
export async function getMarketIndices() {
  if (USE_MOCK) {
    const { mockMarketIndices } = await import("../data/mockMarket.js");
    return mockMarketIndices;
  }
  return request("/api/market/indices");
}

/**
 * GET /api/backtests/latest
 * Returns the most recent backtest performance summary.
 */
export async function getLatestBacktest() {
  if (USE_MOCK) {
    const { mockBacktest } = await import("../data/mockBacktest.js");
    return mockBacktest;
  }
  return request("/api/backtests/latest");
}

/**
 * GET /api/data-health
 * Returns the current data pipeline health status.
 */
export async function getDataHealth() {
  if (USE_MOCK) {
    const { mockDataHealth } = await import("../data/mockMarket.js");
    return mockDataHealth;
  }
  return request("/api/data-health");
}
