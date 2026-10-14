/**
 * @file mockHistory.js
 * @description Deterministic historical OHLCV data for Phase 14 chart rendering.
 *
 * USAGE RULES:
 *   - Only active when VITE_USE_MOCK_DATA=true
 *   - Never presented as real-time or live market data
 *   - Provides up to 260 trading days (1 year) of deterministic OHLCV candles
 */

import { mockOpportunities } from './mockOpportunities.js';
import { mockStocks } from './mockStocks.js';

/**
 * 5-point minimal baseline preserved for backward compatibility.
 */
export const mockStockHistory = [
  { date: '2026-10-08', open: 3480.0, high: 3510.0, low: 3470.0, close: 3495.0, volume: 1250000 },
  { date: '2026-10-09', open: 3495.0, high: 3525.0, low: 3485.0, close: 3505.0, volume: 1420000 },
  { date: '2026-10-10', open: 3510.0, high: 3530.0, low: 3490.0, close: 3500.0, volume: 980000 },
  { date: '2026-10-13', open: 3505.0, high: 3540.0, low: 3498.0, close: 3535.0, volume: 1890000 },
  { date: '2026-10-14', open: 3525.0, high: 3550.0, low: 3515.0, close: 3520.0, volume: 1650000 },
];

/**
 * Deterministic pseudo-random number generator (Mulberry32) seeded by symbol.
 */
function createSeededRandom(seedStr) {
  let h = 1779033703 ^ seedStr.length;
  for (let i = 0; i < seedStr.length; i++) {
    h = Math.imul(h ^ seedStr.charCodeAt(i), 3432918353);
    h = (h << 13) | (h >>> 19);
  }
  return function () {
    h = Math.imul(h ^ (h >>> 16), 2246822507);
    h = Math.imul(h ^ (h >>> 13), 3266489909);
    return ((h ^= h >>> 16) >>> 0) / 4294967296;
  };
}

/**
 * Generates deterministic, realistic daily OHLCV bars for a given symbol.
 * Generates ~260 trading days (weekdays only) ending at the anchor date.
 * 
 * @param {string} symbol
 * @param {number} [targetPrice]
 * @param {number} [count=260]
 * @returns {Array<{date: string, open: number, high: number, low: number, close: number, volume: number}>}
 */
export function generateDeterministicHistory(symbol, targetPrice = 3520, count = 260) {
  const cleanSymbol = (symbol || 'TCS').toUpperCase();
  const rand = createSeededRandom(cleanSymbol);

  // Generate weekday dates going backward
  const anchorDate = new Date('2026-10-14T00:00:00.000Z');
  const dates = [];
  const curr = new Date(anchorDate);

  while (dates.length < count) {
    const dayOfWeek = curr.getUTCDay();
    if (dayOfWeek !== 0 && dayOfWeek !== 6) {
      // Monday to Friday
      dates.unshift(curr.toISOString().slice(0, 10));
    }
    curr.setUTCDate(curr.getUTCDate() - 1);
  }

  // Pre-generate random walk returns working backwards from targetPrice
  const closes = new Array(count);
  closes[count - 1] = targetPrice;

  const volatility = 0.015; // 1.5% daily volatility

  // Generate price path backwards from latest close
  for (let i = count - 2; i >= 0; i--) {
    const r1 = rand();
    const r2 = rand();
    const norm = Math.sqrt(-2.0 * Math.log(r1 || 0.0001)) * Math.cos(2.0 * Math.PI * r2);
    // Slight upward drift for long trends, or downward for bearish setups
    const drift = cleanSymbol === 'BAJFINANCE' ? -0.0003 : 0.0004;
    const dailyReturn = drift + norm * volatility;
    closes[i] = closes[i + 1] / (1 + dailyReturn);
  }

  // Build OHLCV candles
  const candles = [];
  for (let i = 0; i < count; i++) {
    const close = Math.round(closes[i] * 100) / 100;
    const prevClose = i > 0 ? closes[i - 1] : close * (1 - (rand() - 0.5) * 0.01);
    
    // Open is typically close to previous close with minor gap
    const gap = (rand() - 0.49) * 0.006 * prevClose;
    let open = Math.round((prevClose + gap) * 100) / 100;

    // High and Low expand beyond max(open, close) and min(open, close)
    const bodyMax = Math.max(open, close);
    const bodyMin = Math.min(open, close);
    const upperWick = rand() * 0.012 * close;
    const lowerWick = rand() * 0.012 * close;

    const high = Math.round((bodyMax + upperWick) * 100) / 100;
    const low = Math.round(Math.max(bodyMin - lowerWick, close * 0.5) * 100) / 100;

    // Volume with occasional volume surges
    const isSurge = rand() > 0.88;
    const baseVolume = 800000 + Math.floor(rand() * 1200000);
    const volume = isSurge ? baseVolume * (2 + Math.floor(rand() * 2)) : baseVolume;

    candles.push({
      date: dates[i],
      open,
      high,
      low,
      close,
      volume,
    });
  }

  return candles;
}

/**
 * Cache for deterministic mock historical datasets.
 */
const historyCache = new Map();

/**
 * Retrieves mock historical OHLCV data for a given stock symbol.
 * 
 * @param {string} symbol 
 * @param {object} [options]
 * @returns {Array<object>} Array of historical price objects
 */
export function getMockStockHistory(symbol) {
  const cleanSymbol = (symbol || 'TCS').toUpperCase().trim();

  // Return cached result if available
  if (historyCache.has(cleanSymbol)) {
    return historyCache.get(cleanSymbol);
  }

  // Look up current price from mockOpportunities or mockStocks
  let targetPrice = 3520.0;
  const opp = mockOpportunities.find((o) => o.symbol.toUpperCase() === cleanSymbol);
  if (opp && opp.current_price) {
    targetPrice = opp.current_price;
  } else {
    const stock = mockStocks.find((s) => s.symbol.toUpperCase() === cleanSymbol);
    if (stock && stock.current_price) {
      targetPrice = stock.current_price;
    }
  }

  // Special test case: LINE_ONLY stock has only closing prices (no open/high/low)
  if (cleanSymbol === 'LINEONLY') {
    const full = generateDeterministicHistory('TCS', targetPrice, 260);
    const lineOnly = full.map((c) => ({
      date: c.date,
      close: c.close,
      volume: c.volume,
    }));
    historyCache.set(cleanSymbol, lineOnly);
    return lineOnly;
  }

  // Special test case: SHORT_HISTORY stock has only 5 days of data
  if (cleanSymbol === 'SHORTHIST') {
    return mockStockHistory;
  }

  const generated = generateDeterministicHistory(cleanSymbol, targetPrice, 260);
  historyCache.set(cleanSymbol, generated);
  return generated;
}
