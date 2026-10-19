/**
 * @file watchlistStorage.test.js
 * @description Unit test suite for Phase 17 Watchlist & Stock Tracking utilities.
 */

import {
  WATCHLIST_STORAGE_KEY,
  normalizeWatchlistItem,
  loadWatchlist,
  saveWatchlist,
  addStockToWatchlist,
  removeStockFromWatchlist,
  calculatePerformanceSinceAdded,
  filterWatchlist,
  sortWatchlist,
} from './watchlistStorage.js';

let passedTests = 0;
let totalTests = 0;

function assert(condition, message) {
  totalTests++;
  if (!condition) {
    console.error(`❌ FAIL: ${message}`);
    throw new Error(`Test assertion failed: ${message}`);
  }
  passedTests++;
  console.log(`✅ PASS: ${message}`);
}

function assertClose(actual, expected, tolerance = 0.01, message = '') {
  totalTests++;
  const diff = Math.abs(actual - expected);
  if (diff > tolerance) {
    console.error(`❌ FAIL: ${message} (expected ~${expected}, got ${actual})`);
    throw new Error(`Test assertion failed: ${message}`);
  }
  passedTests++;
  console.log(`✅ PASS: ${message} (${actual} ≈ ${expected})`);
}

// In-memory mock storage implementation for tests
function createMockStorage(initial = {}) {
  const store = { ...initial };
  return {
    getItem(key) {
      return store[key] !== undefined ? store[key] : null;
    },
    setItem(key, val) {
      store[key] = String(val);
    },
    removeItem(key) {
      delete store[key];
    },
    clear() {
      for (const k in store) delete store[k];
    },
  };
}

console.log('\n--- Testing Watchlist Item Normalization ---');
{
  assert(normalizeWatchlistItem(null) === null, 'Null item returns null');
  assert(normalizeWatchlistItem('') === null, 'Empty string returns null');
  assert(normalizeWatchlistItem('   ') === null, 'Whitespace string returns null');

  const fromStr = normalizeWatchlistItem('tcs');
  assert(fromStr.symbol === 'TCS', 'String ticker normalized to uppercase TCS');
  assert(fromStr.addedPrice === null, 'String ticker has null addedPrice');
  assert(typeof fromStr.addedAt === 'string', 'String ticker sets addedAt ISO date');

  const fromObj = normalizeWatchlistItem({
    symbol: 'reliance',
    company_name: 'Reliance Industries',
    current_price: 2940.5,
  });
  assert(fromObj.symbol === 'RELIANCE', 'Object symbol normalized to RELIANCE');
  assert(fromObj.company_name === 'Reliance Industries', 'Object company name preserved');
  assert(fromObj.addedPrice === 2940.5, 'addedPrice captured from current_price');

  const withSpecificAddedPrice = normalizeWatchlistItem({
    symbol: 'INFY',
    addedPrice: 1500,
    current_price: 1600,
  });
  assert(withSpecificAddedPrice.addedPrice === 1500, 'Explicit addedPrice takes precedence');
}

console.log('\n--- Testing Watchlist Add & Duplicate Prevention ---');
{
  const list0 = [];
  const res1 = addStockToWatchlist(list0, { symbol: 'TCS', current_price: 3500 });
  assert(res1.success === true, 'Adding TCS succeeds');
  assert(res1.list.length === 1, 'List has 1 item');
  assert(res1.isDuplicate === false, 'isDuplicate is false');
  assert(res1.item.addedPrice === 3500, 'addedPrice is 3500');

  // Attempt duplicate add
  const res2 = addStockToWatchlist(res1.list, { symbol: 'tcs', current_price: 3600 });
  assert(res2.success === false, 'Duplicate add returns success: false');
  assert(res2.isDuplicate === true, 'isDuplicate flag is true');
  assert(res2.list.length === 1, 'List remains length 1');

  // Add another unique stock
  const res3 = addStockToWatchlist(res1.list, 'HDFCBANK');
  assert(res3.success === true, 'Adding HDFCBANK succeeds');
  assert(res3.list.length === 2, 'List now has 2 items');
}

console.log('\n--- Testing Watchlist Removal ---');
{
  const list = [
    { symbol: 'TCS', addedPrice: 3500 },
    { symbol: 'INFY', addedPrice: 1500 },
  ];
  const res = removeStockFromWatchlist(list, 'tcs');
  assert(res.success === true, 'Removing TCS succeeds');
  assert(res.list.length === 1, 'List length reduced to 1');
  assert(res.list[0].symbol === 'INFY', 'Remaining item is INFY');
  assert(res.removedItem.symbol === 'TCS', 'Removed item returned');

  const resNotFound = removeStockFromWatchlist(res.list, 'UNKNOWN');
  assert(resNotFound.success === false, 'Removing non-existent item returns false');
  assert(resNotFound.list.length === 1, 'List length unchanged');
}

console.log('\n--- Testing Performance Since Added Calculation ---');
{
  assert(calculatePerformanceSinceAdded(null, 100) === null, 'Null current price yields null');
  assert(calculatePerformanceSinceAdded(100, null) === null, 'Null added price yields null');
  assert(calculatePerformanceSinceAdded(100, 0) === null, 'Zero added price yields null to avoid div by zero');

  // 100 -> 110 (+10%)
  assertClose(calculatePerformanceSinceAdded(110, 100), 10.0, 0.01, '100 to 110 is +10%');

  // 100 -> 90 (-10%)
  assertClose(calculatePerformanceSinceAdded(90, 100), -10.0, 0.01, '100 to 90 is -10%');

  // 3500 -> 3675 (+5%)
  assertClose(calculatePerformanceSinceAdded(3675, 3500), 5.0, 0.01, '3500 to 3675 is +5%');
}

console.log('\n--- Testing Watchlist Storage Loading & Saving ---');
{
  const mockStorage = createMockStorage();
  assert(loadWatchlist(mockStorage).length === 0, 'Empty storage returns empty array');

  // Corrupted JSON recovery
  mockStorage.setItem(WATCHLIST_STORAGE_KEY, '{invalid json');
  assert(loadWatchlist(mockStorage).length === 0, 'Corrupted JSON safely returns empty array');

  // Legacy string array migration
  mockStorage.setItem(WATCHLIST_STORAGE_KEY, JSON.stringify(['TCS', 'RELIANCE', 'TCS']));
  const loadedLegacy = loadWatchlist(mockStorage);
  assert(loadedLegacy.length === 2, 'Legacy string array migrated and deduplicated');
  assert(loadedLegacy[0].symbol === 'TCS', 'First legacy item is TCS');
  assert(loadedLegacy[1].symbol === 'RELIANCE', 'Second legacy item is RELIANCE');

  // Save new items
  const savedOk = saveWatchlist(loadedLegacy, mockStorage);
  assert(savedOk === true, 'saveWatchlist returns true');
  const reloaded = loadWatchlist(mockStorage);
  assert(reloaded.length === 2, 'Reloaded list has 2 items');
}

console.log('\n--- Testing Watchlist Filtering (Search, Gainers, Decliners) ---');
{
  const stocks = [
    { symbol: 'TCS', company_name: 'Tata Consultancy Services', change_percent: 1.5 },
    { symbol: 'INFY', company_name: 'Infosys Limited', change_percent: -0.8 },
    { symbol: 'TATAMOTORS', company_name: 'Tata Motors Limited', change_percent: 2.2 },
  ];

  // Search by symbol
  const searchSym = filterWatchlist(stocks, { search: 'INFY' });
  assert(searchSym.length === 1 && searchSym[0].symbol === 'INFY', 'Search matches INFY');

  // Search by company name
  const searchName = filterWatchlist(stocks, { search: 'Tata' });
  assert(searchName.length === 2, 'Search "Tata" matches TCS and TATAMOTORS');

  // Filter GAINERS
  const gainers = filterWatchlist(stocks, { filter: 'GAINERS' });
  assert(gainers.length === 2, 'Gainers filter returns 2 stocks');
  assert(gainers.every(s => s.change_percent > 0), 'All returned are positive change');

  // Filter DECLINERS
  const decliners = filterWatchlist(stocks, { filter: 'DECLINERS' });
  assert(decliners.length === 1 && decliners[0].symbol === 'INFY', 'Decliners filter returns INFY');
}

console.log('\n--- Testing Watchlist Sorting ---');
{
  const stocks = [
    { symbol: 'TCS', current_price: 3500, change_percent: 1.5, addedPrice: 3000, addedAt: '2026-01-01', opportunity_score: 80 },
    { symbol: 'INFY', current_price: 1500, change_percent: -1.0, addedPrice: 1600, addedAt: '2026-02-01', opportunity_score: 70 },
    { symbol: 'RELIANCE', current_price: 2900, change_percent: 3.0, addedPrice: 2900, addedAt: '2026-03-01', opportunity_score: 90 },
  ];

  // Sort by symbol asc
  const bySym = sortWatchlist(stocks, 'symbol-asc');
  assert(bySym[0].symbol === 'INFY' && bySym[2].symbol === 'TCS', 'Symbol asc sorts INFY -> RELIANCE -> TCS');

  // Sort by price desc
  const byPrice = sortWatchlist(stocks, 'price-desc');
  assert(byPrice[0].symbol === 'TCS' && byPrice[2].symbol === 'INFY', 'Price desc sorts TCS (3500) first');

  // Sort by daily change desc
  const byChange = sortWatchlist(stocks, 'change-desc');
  assert(byChange[0].symbol === 'RELIANCE' && byChange[2].symbol === 'INFY', 'Daily change desc sorts RELIANCE (+3%) first');

  // Sort by performance since added desc
  // TCS: (3500-3000)/3000 = +16.6%
  // RELIANCE: 0%
  // INFY: (1500-1600)/1600 = -6.25%
  const byPerf = sortWatchlist(stocks, 'perf-desc');
  assert(byPerf[0].symbol === 'TCS', 'Performance since added desc sorts TCS (+16.6%) first');
  assert(byPerf[2].symbol === 'INFY', 'Performance since added desc sorts INFY (-6.25%) last');

  // Sort by date added desc (newest first)
  const byAdded = sortWatchlist(stocks, 'added-desc');
  assert(byAdded[0].symbol === 'RELIANCE', 'Added desc sorts RELIANCE (March) first');
}

console.log(`\n🎉 All ${passedTests} watchlist storage tests passed successfully (${totalTests} total).`);
