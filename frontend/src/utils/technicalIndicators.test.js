/**
 * @file technicalIndicators.test.js
 * @description Unit tests for EMA, RSI, and MACD calculation functions.
 * Tests include:
 *   - Mathematical accuracy against known reference values
 *   - Insufficient datasets (< 14, < 20, < 26, < 34, < 50, < 200, 0, 1)
 *   - Constant prices
 *   - Missing / null data handling
 *   - Strict non-fabrication of data
 */

import {
  calculateEMA,
  calculateRSI,
  calculateMACD,
  computeAllIndicators,
  getRsiZone,
  getMacdStatus,
  getEmaAlignment,
} from './technicalIndicators.js';

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

function assertClose(actual, expected, tolerance = 0.05, message = '') {
  totalTests++;
  const diff = Math.abs(actual - expected);
  if (diff > tolerance) {
    console.error(`❌ FAIL: ${message} (Expected ~${expected}, got ${actual}, diff ${diff})`);
    throw new Error(`${message}: Expected ~${expected}, got ${actual}`);
  } else {
    passedTests++;
    console.log(`✅ PASS: ${message} (${actual} ≈ ${expected})`);
  }
}

console.log('--- Testing EMA Calculations ---');

// 1. Empty & Insufficient data
assert(calculateEMA([], 20).length === 0, 'Empty data returns empty array');
const threeItems = [{ close: 100 }, { close: 105 }, { close: 110 }];
const ema3Period20 = calculateEMA(threeItems, 20);
assert(ema3Period20.length === 3, 'Length matches input');
assert(ema3Period20.every((v) => v === null), 'All elements are null when length < period (no fabrication)');

// 2. Constant prices
const constPrices = Array.from({ length: 25 }, () => ({ close: 150 }));
const emaConst = calculateEMA(constPrices, 20);
assert(emaConst[18] === null, 'Index 18 is null for period 20');
assertClose(emaConst[19], 150, 0.001, 'EMA at period-1 equals constant price');
assertClose(emaConst[24], 150, 0.001, 'EMA subsequent points remain constant price');

// 3. Known series verification: 5-period EMA on [10, 11, 12, 13, 14, 15]
// SMA of first 5: (10+11+12+13+14)/5 = 12
// k = 2 / (5 + 1) = 2/6 = 1/3
// EMA_5 = 15 * (1/3) + 12 * (2/3) = 5 + 8 = 13
const knownSeries = [10, 11, 12, 13, 14, 15].map((c) => ({ close: c }));
const ema5 = calculateEMA(knownSeries, 5);
assert(ema5[0] === null && ema5[3] === null, 'Indices 0-3 are null for 5-period EMA');
assertClose(ema5[4], 12, 0.01, 'Initial 5-period EMA is SMA = 12');
assertClose(ema5[5], 13, 0.01, 'Subsequent EMA is 13');

console.log('\n--- Testing RSI Calculations ---');

// 4. Insufficient RSI data
assert(calculateRSI([], 14).length === 0, 'Empty data returns empty array');
const shortSeries = Array.from({ length: 14 }, (_, i) => ({ close: 100 + i }));
const rsiShort = calculateRSI(shortSeries, 14);
assert(rsiShort.length === 14 && rsiShort.every((v) => v === null), 'RSI is null for length <= 14');

// 5. Constant prices RSI
const flatSeries = Array.from({ length: 30 }, () => ({ close: 200 }));
const rsiFlat = calculateRSI(flatSeries, 14);
assert(rsiFlat[13] === null, 'RSI null before 14th change');
assert(rsiFlat[14] === 50, 'RSI for constant prices is 50 (neutral)');
assert(rsiFlat[29] === 50, 'RSI remains 50 on flat prices');

// 6. Monotonically increasing prices (all gains, no loss)
const bullSeries = Array.from({ length: 25 }, (_, i) => ({ close: 100 + i * 2 }));
const rsiBull = calculateRSI(bullSeries, 14);
assertClose(rsiBull[14], 100, 0.01, 'RSI with all gains and zero losses is 100');

// 7. Monotonically decreasing prices (all losses, no gain)
const bearSeries = Array.from({ length: 25 }, (_, i) => ({ close: 200 - i * 2 }));
const rsiBear = calculateRSI(bearSeries, 14);
assertClose(rsiBear[14], 0, 0.01, 'RSI with all losses and zero gains is 0');

// 8. Standard 14-period RSI known series (Wilder's smoothing)
// 15 prices: [44.34, 44.09, 44.15, 43.61, 44.33, 44.83, 45.10, 45.42, 45.84, 46.08, 45.89, 46.03, 45.61, 46.28, 46.28]
const wilderPrices = [
  44.34, 44.09, 44.15, 43.61, 44.33, 44.83, 45.10, 45.42, 45.84, 46.08, 45.89, 46.03, 45.61, 46.28, 46.28
].map((p) => ({ close: p }));
const rsiWilder = calculateRSI(wilderPrices, 14);
assert(rsiWilder[13] === null, 'RSI index 13 is null');
assert(rsiWilder[14] !== null, 'RSI index 14 is defined');
// Known Wilder 14-period RSI for this sequence is ~70.53
assertClose(rsiWilder[14], 70.53, 1.0, 'Wilder RSI calculation matches standard value (~70.5)');

console.log('\n--- Testing MACD Calculations ---');

// 9. Insufficient MACD data
const macdShort = calculateMACD(Array.from({ length: 20 }, () => ({ close: 100 })));
assert(macdShort.every((item) => item.macd === null && item.signal === null && item.histogram === null), 'All null when < 26');

// 10. Constant prices MACD
const macdConst = calculateMACD(Array.from({ length: 50 }, () => ({ close: 250 })));
assert(macdConst[25].macd === 0, 'MACD is 0 for constant prices');
assert(macdConst[33].signal === 0, 'Signal is 0 for constant prices');
assert(macdConst[33].histogram === 0, 'Histogram is 0 for constant prices');

// 11. Full length MACD structure
const fullHistory = Array.from({ length: 260 }, (_, i) => ({
  date: `2026-01-${String(i % 28 + 1).padStart(2, '0')}`,
  close: 1000 + Math.sin(i / 10) * 100 + i * 2,
}));
const allInds = computeAllIndicators(fullHistory);
assert(allInds.sufficiency.hasEma20 === true, 'hasEma20 is true for 260 bars');
assert(allInds.sufficiency.hasEma50 === true, 'hasEma50 is true for 260 bars');
assert(allInds.sufficiency.hasEma200 === true, 'hasEma200 is true for 260 bars');
assert(allInds.sufficiency.hasRsi === true, 'hasRsi is true for 260 bars');
assert(allInds.sufficiency.hasMacd === true, 'hasMacd is true for 260 bars');
assert(allInds.latest.ema20 !== null, 'latest EMA 20 is defined');
assert(allInds.latest.ema50 !== null, 'latest EMA 50 is defined');
assert(allInds.latest.ema200 !== null, 'latest EMA 200 is defined');
assert(allInds.latest.rsi >= 0 && allInds.latest.rsi <= 100, 'latest RSI in [0, 100]');
assert(allInds.latest.macd !== null, 'latest MACD is defined');
assert(allInds.latest.signal !== null, 'latest Signal is defined');
assert(allInds.latest.histogram !== null, 'latest Histogram is defined');

console.log('\n--- Testing Educational Classifications ---');

// 12. RSI Zone
assert(getRsiZone(75).zone === 'OVERBOUGHT', 'RSI 75 classified as Overbought');
assert(getRsiZone(25).zone === 'OVERSOLD', 'RSI 25 classified as Oversold');
assert(getRsiZone(50).zone === 'NEUTRAL', 'RSI 50 classified as Neutral');
assert(getRsiZone(null).zone === 'INSUFFICIENT', 'null RSI classified as Insufficient');

// 13. MACD Status
const bullMacd = getMacdStatus(5.2, 3.1, 2.1);
assert(bullMacd.status === 'BULLISH', 'Positive histogram is Bullish');
const bearMacd = getMacdStatus(-2.0, -1.0, -1.0);
assert(bearMacd.status === 'BEARISH', 'Negative histogram is Bearish');

// 14. EMA Alignment
const bullAlign = getEmaAlignment(120, 110, 100, 90);
assert(bullAlign.status === 'BULLISH_STACK', 'Price > EMA20 > EMA50 > EMA200 is Bullish Stack');

console.log('\n--- Testing Edge Case Mock Scenarios ---');

// 15. SHORTHIST (5 bars only): All indicators must be null, no fabrication
const short5Bars = [
  { date: '2026-10-08', close: 3495.0 },
  { date: '2026-10-09', close: 3505.0 },
  { date: '2026-10-10', close: 3500.0 },
  { date: '2026-10-13', close: 3535.0 },
  { date: '2026-10-14', close: 3520.0 },
];
const shortInds = computeAllIndicators(short5Bars);
assert(shortInds.sufficiency.hasEma20 === false, 'SHORTHIST: hasEma20 is false');
assert(shortInds.sufficiency.hasEma50 === false, 'SHORTHIST: hasEma50 is false');
assert(shortInds.sufficiency.hasEma200 === false, 'SHORTHIST: hasEma200 is false');
assert(shortInds.sufficiency.hasRsi === false, 'SHORTHIST: hasRsi is false');
assert(shortInds.sufficiency.hasMacd === false, 'SHORTHIST: hasMacd is false');
assert(shortInds.latest.ema20 === null, 'SHORTHIST: latest EMA 20 is null');
assert(shortInds.latest.rsi === null, 'SHORTHIST: latest RSI is null');
assert(shortInds.latest.macd === null, 'SHORTHIST: latest MACD is null');

// 16. LINEONLY (260 bars of close prices only, without open/high/low)
const lineOnlyBars = Array.from({ length: 260 }, (_, i) => ({
  date: `2026-01-${String(i % 28 + 1).padStart(2, '0')}`,
  close: 3000 + (i * 1.5) + (i % 5),
}));
const lineInds = computeAllIndicators(lineOnlyBars);
assert(lineInds.sufficiency.hasEma20 === true, 'LINEONLY: hasEma20 is true');
assert(lineInds.sufficiency.hasEma50 === true, 'LINEONLY: hasEma50 is true');
assert(lineInds.sufficiency.hasEma200 === true, 'LINEONLY: hasEma200 is true');
assert(lineInds.sufficiency.hasRsi === true, 'LINEONLY: hasRsi is true');
assert(lineInds.sufficiency.hasMacd === true, 'LINEONLY: hasMacd is true');
assert(lineInds.latest.ema20 !== null, 'LINEONLY: latest EMA 20 is computed from close prices');
assert(lineInds.latest.rsi !== null, 'LINEONLY: latest RSI is computed from close prices');

// 17. Missing/NaN data in series handled safely
const corruptedData = [
  { close: 100 },
  { close: null },
  { close: undefined },
  { close: NaN },
  { close: 120 },
];
const safeEma = calculateEMA(corruptedData, 3);
assert(safeEma.length === 5, 'Corrupted data returns same length array');
assert(safeEma[safeEma.length - 1] === null, 'Corrupted window produces null safely');

console.log(`\n🎉 All ${passedTests} tests passed successfully (${totalTests} total).`);
