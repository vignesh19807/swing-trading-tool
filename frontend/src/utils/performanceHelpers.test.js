/**
 * @file performanceHelpers.test.js
 * @description Unit tests for Phase 18 Portfolio & Performance Dashboard calculations.
 */

import {
  validateEquitySeries,
  filterEquitySeriesByRange,
  calculateEquityScales,
  calculateWatchlistPortfolioMetrics,
  normalizeBacktestData,
} from './performanceHelpers.js';

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

function assertClose(actual, expected, tolerance = 0.05, message = '') {
  totalTests++;
  const diff = Math.abs(actual - expected);
  if (diff > tolerance) {
    console.error(`❌ FAIL: ${message} (expected ~${expected}, got ${actual})`);
    throw new Error(`Test assertion failed: ${message}`);
  }
  passedTests++;
  console.log(`✅ PASS: ${message} (${actual} ≈ ${expected})`);
}

console.log('\n--- Testing Equity Curve Series Validation ---');
{
  assert(validateEquitySeries(null).isValid === false, 'Null series is invalid');
  assert(validateEquitySeries([]).isValid === false, 'Empty series is invalid');
  assert(validateEquitySeries([{ equity: 1000 }]).isValid === false, 'Single point series is invalid (needs >= 2 points)');

  const corrupted = [
    { equity: null, date: '2025-01-01' },
    { equity: 'invalid', date: '2025-02-01' },
    { equity: -50, date: '2025-03-01' },
  ];
  assert(validateEquitySeries(corrupted).isValid === false, 'Corrupted values yield invalid series');

  const validSeries = [
    { date: '2025-01-01', equity: 100000, drawdown_pct: 0 },
    { date: '2025-02-01', equity: 110000, drawdown_pct: 0 },
    { date: '2025-03-01', equity: 105000, drawdown_pct: 4.54 },
    { date: '2025-04-01', equity: 120000, drawdown_pct: 0 },
  ];

  const res = validateEquitySeries(validSeries);
  assert(res.isValid === true, 'Valid series passes validation');
  assert(res.validCount === 4, 'Valid count matches 4');
  assert(res.startEquity === 100000, 'startEquity matches 100,000');
  assert(res.endEquity === 120000, 'endEquity matches 120,000');
  assert(res.minEquity === 100000, 'minEquity matches 100,000');
  assert(res.maxEquity === 120000, 'maxEquity matches 120,000');
  assertClose(res.totalReturnPct, 20.0, 0.01, 'Total return percentage is +20%');
  assertClose(res.maxDrawdownPct, 4.54, 0.01, 'Max drawdown is ~4.54%');
}

console.log('\n--- Testing Equity Curve Range Filtering ---');
{
  const series = Array.from({ length: 15 }, (_, i) => ({
    date: `2025-${String(i + 1).padStart(2, '0')}-01`,
    equity: 100000 + i * 2000,
  }));

  assert(filterEquitySeriesByRange(series, 'ALL').length === 15, 'ALL range returns all points');
  assert(filterEquitySeriesByRange(series, '6M').length === 7, '6M returns 7 points');
  assert(filterEquitySeriesByRange(series, '3M').length === 4, '3M returns 4 points');
  assert(filterEquitySeriesByRange(null, '6M').length === 0, 'Null series returns empty array safely');
}

console.log('\n--- Testing SVG Equity Scales Calculation ---');
{
  const series = [
    { date: '2025-01-01', equity: 100000 },
    { date: '2025-02-01', equity: 110000 },
    { date: '2025-03-01', equity: 120000 },
  ];

  const scales = calculateEquityScales({
    series,
    width: 600,
    height: 300,
    margin: { top: 20, right: 60, bottom: 30, left: 20 },
  });

  assert(scales !== null, 'calculateEquityScales returns valid scale object');
  assert(scales.chartWidth === 520, 'chartWidth accounts for left and right margins (600 - 80 = 520)');
  assert(scales.chartHeight === 250, 'chartHeight accounts for top and bottom margins (300 - 50 = 250)');
  assert(typeof scales.linePath === 'string' && scales.linePath.startsWith('M '), 'linePath is valid SVG path string');
  assert(typeof scales.areaPath === 'string' && scales.areaPath.endsWith(' Z'), 'areaPath is closed SVG path');
  assert(scales.yTicks.length >= 4, 'Generated at least 4 Y-axis ticks');
}

console.log('\n--- Testing Watchlist Portfolio Metrics Calculation ---');
{
  // Empty watchlist
  const empty = calculateWatchlistPortfolioMetrics([], []);
  assert(empty.totalTracked === 0, 'Empty watchlist yields totalTracked = 0');
  assert(empty.avgReturnSinceAdded === null, 'Empty watchlist avg return is null');

  const watchlist = [
    { symbol: 'TCS', addedPrice: 3000, addedAt: '2026-01-01' },
    { symbol: 'INFY', addedPrice: 1500, addedAt: '2026-02-01' },
    { symbol: 'RELIANCE', addedPrice: null, addedAt: '2026-03-01' }, // No baseline price
  ];

  const universe = [
    { symbol: 'TCS', current_price: 3300, company_name: 'Tata Consultancy' }, // +10%
    { symbol: 'INFY', current_price: 1350, company_name: 'Infosys' }, // -10%
    { symbol: 'RELIANCE', current_price: 2900, company_name: 'Reliance' },
  ];

  const res = calculateWatchlistPortfolioMetrics(watchlist, universe);
  assert(res.totalTracked === 3, 'Total tracked is 3');
  assert(res.pricedCount === 2, 'Priced count is 2 (TCS and INFY)');
  assert(res.gainersCount === 1, '1 gainer (TCS)');
  assert(res.declinersCount === 1, '1 decliner (INFY)');
  assert(res.flatCount === 0, '0 flat');
  assertClose(res.avgReturnSinceAdded, 0.0, 0.01, 'Average return is (+10% - 10%) / 2 = 0.0%');
  assert(res.bestPerformer.symbol === 'TCS', 'Best performer is TCS');
  assert(res.worstPerformer.symbol === 'INFY', 'Worst performer is INFY');
  assert(res.stocks.length === 3, 'Merged stocks has 3 records');
  assert(res.stocks[0].priceDifference === 300, 'TCS price difference is +₹300');
}

console.log('\n--- Testing Backtest Data Normalization ---');
{
  // Null payload handling
  const fromNull = normalizeBacktestData(null);
  assert(fromNull.total_trades === 0, 'Null payload yields 0 trades');
  assert(fromNull.hasEquityCurve === false, 'Null payload hasEquityCurve is false');
  assert(fromNull.hasMonthlyReturns === false, 'Null payload hasMonthlyReturns is false');

  // Payload without equity curve
  const noCurvePayload = {
    strategy_name: 'Test Strategy',
    total_trades: 50,
    closed_trades: 40,
    winning_trades: 25,
    losing_trades: 15,
    win_rate: 62.5,
    profit_factor: 1.7,
    max_drawdown: 10.5,
  };

  const norm1 = normalizeBacktestData(noCurvePayload);
  assert(norm1.strategy_name === 'Test Strategy', 'Preserves strategy name');
  assert(norm1.win_rate === 62.5, 'Preserves win rate');
  assert(norm1.profit_factor === 1.7, 'Preserves profit factor');
  assert(norm1.max_drawdown_pct === 10.5, 'Normalizes max_drawdown_pct');
  assert(norm1.hasEquityCurve === false, 'Detects missing equity curve correctly');
  assert(norm1.hasMonthlyReturns === false, 'Detects missing monthly returns correctly');

  // Payload with valid equity curve and monthly returns
  const fullPayload = {
    ...noCurvePayload,
    equity_curve: [
      { date: '2025-01-01', equity: 100000 },
      { date: '2025-02-01', equity: 110000 },
    ],
    monthly_returns: [
      { month: 'Jan 2025', return_pct: 10.0 },
    ],
  };

  const norm2 = normalizeBacktestData(fullPayload);
  assert(norm2.hasEquityCurve === true, 'Detects valid equity curve');
  assert(norm2.hasMonthlyReturns === true, 'Detects valid monthly returns');
  assert(norm2.equity_curve.length === 2, 'Equity curve has 2 points');
}

console.log(`\n🎉 All ${passedTests} performance helper tests passed successfully (${totalTests} total).`);
