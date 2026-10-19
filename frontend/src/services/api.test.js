/**
 * @file api.test.js
 * @description Comprehensive unit tests for frontend API service layer (api.js).
 * Validates:
 * 1. Real API Mode: Rejection with explicit configuration error when VITE_API_BASE_URL is missing.
 * 2. Real API Mode: Network error resilience and backend JSON error message parsing.
 * 3. Mock Mode: Successful dynamic loading and payload structures for all 8 API endpoints.
 */

import assert from 'node:assert';
import {
  getOpportunities,
  getStocks,
  getStock,
  getStockHistory,
  getSectors,
  getMarketIndices,
  getLatestBacktest,
  getDataHealth,
} from './api.js';

let passed = 0;
let failed = 0;

async function itAsync(desc, fn) {
  try {
    await fn();
    console.log(`✅ PASS: ${desc}`);
    passed++;
  } catch (err) {
    console.error(`❌ FAIL: ${desc} -> ${err.message}`);
    failed++;
  }
}

// ============================================================================
// PART 1: Real API Mode Configuration Guard (Missing VITE_API_BASE_URL)
// ============================================================================
console.log('\n--- Testing API Service Layer (Real API Mode Guards) ---');

process.env.VITE_USE_MOCK_DATA = 'false';
delete process.env.VITE_API_BASE_URL;

await itAsync('getOpportunities() rejects with configuration error when BASE_URL missing', async () => {
  await assert.rejects(
    () => getOpportunities(),
    /Configuration Error: VITE_API_BASE_URL is missing/
  );
});

await itAsync('getStocks() rejects with configuration error when BASE_URL missing', async () => {
  await assert.rejects(
    () => getStocks(),
    /Configuration Error: VITE_API_BASE_URL is missing/
  );
});

await itAsync('getStock("TCS") rejects with configuration error when BASE_URL missing', async () => {
  await assert.rejects(
    () => getStock('TCS'),
    /Configuration Error: VITE_API_BASE_URL is missing/
  );
});

await itAsync('getStockHistory("TCS") rejects with configuration error when BASE_URL missing', async () => {
  await assert.rejects(
    () => getStockHistory('TCS'),
    /Configuration Error: VITE_API_BASE_URL is missing/
  );
});

await itAsync('getSectors() rejects with configuration error when BASE_URL missing', async () => {
  await assert.rejects(
    () => getSectors(),
    /Configuration Error: VITE_API_BASE_URL is missing/
  );
});

await itAsync('getMarketIndices() rejects with configuration error when BASE_URL missing', async () => {
  await assert.rejects(
    () => getMarketIndices(),
    /Configuration Error: VITE_API_BASE_URL is missing/
  );
});

await itAsync('getLatestBacktest() rejects with configuration error when BASE_URL missing', async () => {
  await assert.rejects(
    () => getLatestBacktest(),
    /Configuration Error: VITE_API_BASE_URL is missing/
  );
});

await itAsync('getDataHealth() rejects with configuration error when BASE_URL missing', async () => {
  await assert.rejects(
    () => getDataHealth(),
    /Configuration Error: VITE_API_BASE_URL is missing/
  );
});

// ============================================================================
// PART 2: Real API Error Parsing & Network Failure Simulation
// ============================================================================
console.log('\n--- Testing API Service Layer (Error & Response Parsing) ---');

process.env.VITE_USE_MOCK_DATA = 'false';
process.env.VITE_API_BASE_URL = 'http://mock-test-server:9999';

const originalFetch = globalThis.fetch;

// Simulate backend 404 with JSON error body
globalThis.fetch = async () => ({
  ok: false,
  status: 404,
  statusText: 'Not Found',
  json: async () => ({
    error: {
      code: 'STOCK_NOT_FOUND',
      message: 'Stock symbol UNKNOWN not found in universe.'
    }
  })
});

await itAsync('request parses JSON error message from backend response', async () => {
  await assert.rejects(
    () => getStock('UNKNOWN'),
    (err) => {
      assert.strictEqual(err.status, 404);
      assert.strictEqual(err.message, 'Stock symbol UNKNOWN not found in universe.');
      return true;
    }
  );
});

// Simulate network failure (DNS / connection refused)
globalThis.fetch = async () => {
  throw new Error('connect ECONNREFUSED 127.0.0.1:9999');
};

await itAsync('request surfaces clear Network Error on connection failure', async () => {
  await assert.rejects(
    () => getOpportunities(),
    /Network Error: Failed to reach the API/
  );
});

// Restore global fetch
globalThis.fetch = originalFetch;

// ============================================================================
// PART 3: Mock Mode Fixture Validation
// ============================================================================
console.log('\n--- Testing API Service Layer (Mock Mode Fixtures) ---');

process.env.VITE_USE_MOCK_DATA = 'true';

await itAsync('getOpportunities() returns valid fixtures array in mock mode', async () => {
  const opps = await getOpportunities();
  assert(Array.isArray(opps), 'Opportunities must be an array');
  assert(opps.length > 0, 'Opportunities must not be empty');
  assert(opps[0].symbol, 'Opportunity item must have a symbol');
});

await itAsync('getStocks() returns stock universe list in mock mode', async () => {
  const stocks = await getStocks();
  assert(Array.isArray(stocks) || (stocks && Array.isArray(stocks.stocks)), 'Stocks must be an array');
});

await itAsync('getStock("TCS") returns intelligence report in mock mode', async () => {
  const stock = await getStock('TCS');
  assert(stock != null, 'Stock intelligence must not be null');
  assert.strictEqual(stock.symbol, 'TCS');
});

await itAsync('getStockHistory("TCS") returns OHLCV series in mock mode', async () => {
  const history = await getStockHistory('TCS');
  assert(Array.isArray(history), 'History must be an array');
  assert(history.length > 0, 'History series must not be empty');
});

await itAsync('getSectors() returns sector rankings in mock mode', async () => {
  const sectors = await getSectors();
  assert(Array.isArray(sectors) || (sectors && Array.isArray(sectors.sectors)), 'Sectors must be an array');
});

await itAsync('getMarketIndices() returns market overview in mock mode', async () => {
  const indices = await getMarketIndices();
  assert(indices != null, 'Market indices must not be null');
  assert(indices.nifty50 != null, 'Must contain nifty50');
});

await itAsync('getLatestBacktest() returns backtest metrics in mock mode', async () => {
  const backtest = await getLatestBacktest();
  assert(backtest != null, 'Backtest must not be null');
  assert(backtest.metrics != null || backtest.win_rate != null, 'Backtest must contain metrics');
});

await itAsync('getDataHealth() returns data pipeline status in mock mode', async () => {
  const health = await getDataHealth();
  assert(health != null, 'Health data must not be null');
});

console.log(`\n🎉 All ${passed} API service unit tests passed successfully (${passed} passed, ${failed} failed).\n`);

if (failed > 0) {
  process.exit(1);
}
