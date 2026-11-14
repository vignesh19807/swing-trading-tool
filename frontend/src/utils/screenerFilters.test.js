/**
 * @file screenerFilters.test.js
 * @description Unit tests for stock screener filtering, strategy filters, sorting, and edge cases.
 */

import {
  DEFAULT_SCREENER_FILTERS,
  matchesScreenerFilters,
  filterStocks,
  sortStocks,
  countActiveFilters,
  getActiveFilterChips,
  getTechnicalSnapshot,
} from './screenerFilters.js';
import { calculateScales } from './chartHelpers.js';

let totalTests = 0;
let passedTests = 0;

function assert(condition, message) {
  totalTests++;
  if (!condition) {
    console.error(`❌ FAIL: ${message}`);
    throw new Error(message);
  } else {
    passedTests++;
    console.log(`✅ PASS: ${message}`);
  }
}

console.log('--- Testing Screener Filter Logic ---');

const mockStock1 = {
  symbol: 'TCS',
  company_name: 'Tata Consultancy Services Ltd',
  sector: 'Information Technology',
  industry: 'IT Services',
  current_price: 3520.0,
  change_percent: 1.45,
  opportunity_score: 78.5,
  recommendation: 'BUY',
};

const mockStock2 = {
  symbol: 'RELIANCE',
  company_name: 'Reliance Industries Ltd',
  sector: 'Energy',
  industry: 'Oil & Gas',
  current_price: 2940.5,
  change_percent: -0.82,
  opportunity_score: 65.0,
  recommendation: 'WATCH',
};

const mockStock3 = {
  symbol: 'BAJFINANCE',
  company_name: 'Bajaj Finance Ltd',
  sector: 'Financial Services',
  industry: 'NBFC',
  current_price: 6850.0,
  change_percent: -2.30,
  opportunity_score: 48.2,
  recommendation: 'SELL',
};

// 1. Default filters match all stocks
assert(matchesScreenerFilters(mockStock1, DEFAULT_SCREENER_FILTERS), 'Default filters match Stock 1');
assert(matchesScreenerFilters(mockStock2, DEFAULT_SCREENER_FILTERS), 'Default filters match Stock 2');
assert(countActiveFilters(DEFAULT_SCREENER_FILTERS) === 0, 'Default filters count is 0');

// 2. Search query matching
const searchFilters = { ...DEFAULT_SCREENER_FILTERS, search: 'tata' };
assert(matchesScreenerFilters(mockStock1, searchFilters), 'Search matches company name "Tata"');
assert(!matchesScreenerFilters(mockStock2, searchFilters), 'Search rejects non-matching stock');

const symbolSearch = { ...DEFAULT_SCREENER_FILTERS, search: 'rel' };
assert(matchesScreenerFilters(mockStock2, symbolSearch), 'Search matches symbol "RELIANCE"');

// 3. Sector filter
const techSector = { ...DEFAULT_SCREENER_FILTERS, sector: 'Information Technology' };
assert(matchesScreenerFilters(mockStock1, techSector), 'Sector matches IT');
assert(!matchesScreenerFilters(mockStock2, techSector), 'Sector rejects Energy');

// 4. Recommendation & Direction filter
const buyFilter = { ...DEFAULT_SCREENER_FILTERS, recommendation: 'BUY' };
assert(matchesScreenerFilters(mockStock1, buyFilter), 'Recommendation matches BUY');
assert(!matchesScreenerFilters(mockStock2, buyFilter), 'Recommendation rejects WATCH');

const bullDirFilter = { ...DEFAULT_SCREENER_FILTERS, direction: 'BULLISH' };
assert(matchesScreenerFilters(mockStock1, bullDirFilter), 'Direction matches Bullish');
assert(!matchesScreenerFilters(mockStock3, bullDirFilter), 'Direction rejects Bearish');

// 5. Price change ranges
const gainers = { ...DEFAULT_SCREENER_FILTERS, changeRange: 'POSITIVE' };
assert(matchesScreenerFilters(mockStock1, gainers), 'Gainers filter matches positive change');
assert(!matchesScreenerFilters(mockStock2, gainers), 'Gainers filter rejects negative change');

const strongDeclines = { ...DEFAULT_SCREENER_FILTERS, changeRange: 'STRONG_DECLINE' };
assert(matchesScreenerFilters(mockStock3, strongDeclines), 'Strong decline matches -2.30%');
assert(!matchesScreenerFilters(mockStock2, strongDeclines), 'Strong decline rejects -0.82%');

// 6. Price range presets & custom
const under3000 = { ...DEFAULT_SCREENER_FILTERS, priceRange: '500_TO_2000' };
assert(!matchesScreenerFilters(mockStock1, under3000), '₹3520 rejected from 500_TO_2000');

const customPrice = { ...DEFAULT_SCREENER_FILTERS, minPrice: 3000, maxPrice: 4000 };
assert(matchesScreenerFilters(mockStock1, customPrice), '₹3520 matches [3000, 4000]');
assert(!matchesScreenerFilters(mockStock2, customPrice), '₹2940 rejected from [3000, 4000]');

console.log('\n--- Testing Technical Strategy Filters ---');

const techSnapshot1 = {
  ema20: 3480.0,
  ema50: 3400.0,
  ema200: 3200.0,
  rsi: 62.5,
  macd: 25.4,
  signal: 18.2,
  histogram: 7.2,
  sufficiency: { hasEma20: true, hasEma50: true, hasEma200: true, hasRsi: true, hasMacd: true, totalBars: 260 },
};

const techSnapshot2 = {
  ema20: 2980.0,
  ema50: 3010.0,
  ema200: 3050.0,
  rsi: 28.4, // Oversold
  macd: -12.0,
  signal: -8.0,
  histogram: -4.0,
  sufficiency: { hasEma20: true, hasEma50: true, hasEma200: true, hasRsi: true, hasMacd: true, totalBars: 260 },
};

// Stock with insufficient history
const insufficientStock = {
  symbol: 'SHORTHIST',
  company_name: 'Short History Test Stock',
  current_price: 150.0,
};
const insufficientTech = {
  ema20: null,
  ema50: null,
  ema200: null,
  rsi: null,
  macd: null,
  signal: null,
  histogram: null,
  sufficiency: { hasEma20: false, hasEma50: false, hasEma200: false, hasRsi: false, hasMacd: false, totalBars: 5 },
  isInsufficient: true,
};

// 7. EMA 20 Above / Below
const aboveEma20 = { ...DEFAULT_SCREENER_FILTERS, priceVsEma20: 'ABOVE' };
assert(matchesScreenerFilters(mockStock1, aboveEma20, techSnapshot1), 'Price 3520 > EMA20 3480 matches ABOVE');
assert(!matchesScreenerFilters(mockStock2, aboveEma20, techSnapshot2), 'Price 2940 < EMA20 2980 rejected from ABOVE');
assert(!matchesScreenerFilters(insufficientStock, aboveEma20, insufficientTech), 'Insufficient history rejected from EMA filter (never fabricated)');

const belowEma20 = { ...DEFAULT_SCREENER_FILTERS, priceVsEma20: 'BELOW' };
assert(matchesScreenerFilters(mockStock2, belowEma20, techSnapshot2), 'Price 2940 < EMA20 2980 matches BELOW');

// 8. RSI Range filters
const rsiOversold = { ...DEFAULT_SCREENER_FILTERS, rsiRange: 'OVERSOLD' };
assert(matchesScreenerFilters(mockStock2, rsiOversold, techSnapshot2), 'RSI 28.4 matches OVERSOLD (< 30)');
assert(!matchesScreenerFilters(mockStock1, rsiOversold, techSnapshot1), 'RSI 62.5 rejected from OVERSOLD');
assert(!matchesScreenerFilters(insufficientStock, rsiOversold, insufficientTech), 'Null RSI rejected from RSI filter');

const rsiBullish = { ...DEFAULT_SCREENER_FILTERS, rsiRange: 'NEUTRAL_HIGH' };
assert(matchesScreenerFilters(mockStock1, rsiBullish, techSnapshot1), 'RSI 62.5 matches 50-70 NEUTRAL_HIGH');

// 9. MACD Crossover and Histogram
const macdBullish = { ...DEFAULT_SCREENER_FILTERS, macdVsSignal: 'ABOVE', macdHistogram: 'POSITIVE' };
assert(matchesScreenerFilters(mockStock1, macdBullish, techSnapshot1), 'MACD 25.4 > 18.2 and Hist 7.2 > 0 matches');
assert(!matchesScreenerFilters(mockStock2, macdBullish, techSnapshot2), 'MACD -12 < -8 rejected');
assert(!matchesScreenerFilters(insufficientStock, macdBullish, insufficientTech), 'Insufficient MACD rejected');

console.log('\n--- Testing Sorting Functions ---');

const stockList = [mockStock1, mockStock2, mockStock3];
const techMap = new Map([
  ['TCS', techSnapshot1],
  ['RELIANCE', techSnapshot2],
  ['BAJFINANCE', null],
]);

// Sort by price desc
const sortedPriceDesc = sortStocks(stockList, 'price-desc');
assert(sortedPriceDesc[0].symbol === 'BAJFINANCE', 'Highest price is BAJFINANCE (6850)');
assert(sortedPriceDesc[2].symbol === 'RELIANCE', 'Lowest price is RELIANCE (2940.5)');

// Sort by change desc
const sortedChangeDesc = sortStocks(stockList, 'change-desc');
assert(sortedChangeDesc[0].symbol === 'TCS', 'Highest gain is TCS (+1.45%)');
assert(sortedChangeDesc[2].symbol === 'BAJFINANCE', 'Lowest change is BAJFINANCE (-2.30%)');

// Sort by RSI desc
const sortedRsiDesc = sortStocks(stockList, 'rsi-desc', techMap);
assert(sortedRsiDesc[0].symbol === 'TCS', 'Highest RSI is TCS (62.5)');
assert(sortedRsiDesc[1].symbol === 'RELIANCE', 'Second RSI is RELIANCE (28.4)');

console.log('\n--- Testing Filter Chips and Active Count ---');

const activeFilters = {
  ...DEFAULT_SCREENER_FILTERS,
  search: 'tata',
  sector: 'Information Technology',
  priceVsEma20: 'ABOVE',
  rsiRange: 'NEUTRAL_HIGH',
};

assert(countActiveFilters(activeFilters) === 4, 'Active filter count is 4');
let removedKey = null;
const chips = getActiveFilterChips(activeFilters, (key) => {
  removedKey = key;
});
assert(chips.length === 4, 'Generated 4 chips');
assert(chips[0].label.includes('tata'), 'Search chip contains query');
assert(chips[2].label.includes('EMA 20'), 'EMA chip contains EMA 20');

// Trigger chip removal callback
chips[2].onRemove();
assert(removedKey === 'priceVsEma20', 'Chip remove callback fired with correct key');

console.log('\n--- Testing filterStocks and getTechnicalSnapshot ---');

// Test getTechnicalSnapshot with empty / null data
const emptySnapshot = getTechnicalSnapshot([]);
assert(emptySnapshot.isInsufficient === true, 'Empty history yields isInsufficient: true');
assert(emptySnapshot.rsi === null, 'Empty history yields rsi: null');
assert(emptySnapshot.ema20 === null, 'Empty history yields ema20: null');

// Test filterStocks batch operation
const batchFiltered = filterStocks(stockList, { ...DEFAULT_SCREENER_FILTERS, sector: 'Information Technology' });
assert(batchFiltered.length === 1 && batchFiltered[0].symbol === 'TCS', 'filterStocks batches correctly for IT sector');

const batchTechFiltered = filterStocks(stockList, { ...DEFAULT_SCREENER_FILTERS, rsiRange: 'OVERSOLD' }, techMap);
assert(batchTechFiltered.length === 1 && batchTechFiltered[0].symbol === 'RELIANCE', 'filterStocks batches correctly with technical snapshot map');

console.log('\n--- Testing calculateScales Geometry and Margin ---');
const dummyBars = [
  { date: '2026-10-10', open: 100, high: 105, low: 98, close: 102, volume: 1000 },
  { date: '2026-10-11', open: 102, high: 108, low: 101, close: 106, volume: 1500 },
];
const customMargin = { top: 24, right: 75, bottom: 34, left: 18 };
const testScales = calculateScales({
  data: dummyBars,
  width: 800,
  height: 400,
  margin: customMargin,
});
assert(testScales !== null, 'calculateScales produces valid scale object');
assert(testScales.margin !== undefined, 'scales contains margin object');
assert(testScales.margin.left === 18, 'scales.margin.left matches input margin');
assert(testScales.margin.right === 75, 'scales.margin.right matches input margin');
assert(testScales.margin.top === 24, 'scales.margin.top matches input margin');
assert(testScales.margin.bottom === 34, 'scales.margin.bottom matches input margin');
assert(Array.isArray(testScales.priceTicks) && testScales.priceTicks.length > 0, 'scales contains price ticks');

console.log(`\n🎉 All ${passedTests} screener tests passed successfully (${totalTests} total).`);
