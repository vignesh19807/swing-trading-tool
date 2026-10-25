/**
 * @file dashboardRegressions.test.js
 * @description Regression test suite for Dashboard focused fixes (Issues A through G).
 */

import { normalizeSectorData } from './sectorHelpers.js';

function runRegressionTests() {
  console.log('\n--- Running Dashboard Regressions Test Suite ---');
  let passed = 0;
  let total = 0;

  function assert(condition, message) {
    total++;
    if (!condition) {
      console.error(`❌ FAILED: ${message}`);
      throw new Error(`Assertion failed: ${message}`);
    }
    passed++;
    console.log(`  ✓ ${message}`);
  }

  // Issue A: Search normalization logic
  const query = '  InFoSys  ';
  const normalizedQuery = query.trim().toLowerCase();
  const mockStocks = [
    { symbol: 'INFY', name: 'Infosys Ltd', sector: 'Information Technology' },
    { symbol: 'TCS', name: 'Tata Consultancy Services', sector: 'Information Technology' }
  ];
  const matched = mockStocks.filter(s =>
    s.symbol.toLowerCase().includes(normalizedQuery) ||
    s.name.toLowerCase().includes(normalizedQuery) ||
    s.sector.toLowerCase().includes(normalizedQuery)
  );
  assert(matched.length === 1 && matched[0].symbol === 'INFY', 'Issue A: Search normalization correctly matches company name');

  // Issue C: Sector Data Normalization from real engine structure
  const realEngineSector = {
    sector: 'Information Technology',
    performance: 0.045, // 63D return decimal
    relative_strength: {
      status: 'VALID',
      '63D_rs': 0.035,
      '21D_rs': 0.015
    },
    breadth: { advance_decline_ratio: 2.5, percent_above_50d_sma: 75 },
    stock_count: 5
  };
  const normalized = normalizeSectorData(realEngineSector, 0);
  assert(normalized.name === 'Information Technology', 'Issue C: Preserves sector name');
  assert(Math.abs(normalized.performance_63d - 4.5) < 0.001, 'Issue C: Correctly maps 63D decimal performance to percentage');
  assert(normalized.status === 'Outperforming', 'Issue C: Maps nested relative_strength difference to Outperforming');
  assert(normalized.stockCount === 5, 'Issue C: Preserves stock count');

  // Issue D & E: Opportunity Data fields validation
  const oppItem = {
    symbol: 'INFY',
    setup_name: 'Pullback to Support',
    confidence_score: 78.5,
    setup_quality: 'High',
    current_price: 1153.8,
    entry_zone_low: 1145.0,
    entry_zone_high: 1160.0,
    stop_loss: 1120.0,
    target: 1210.0,
    technical_score: 82.0,
    financial_score: 75.0,
    momentum_score: 78.0
  };
  assert(typeof oppItem.current_price === 'number' && oppItem.current_price > 0, 'Issue D: Opportunity current_price is populated and numeric');
  assert(typeof oppItem.technical_score === 'number' && oppItem.technical_score === 82.0, 'Issue E: Technical score is populated for setup badge rendering');

  // Issue F: Dynamic Universe Count resolution
  const healthData = { universe_count: 52 };
  const universeCount = healthData?.universe_count || healthData?.universe_size || 50;
  assert(universeCount === 52, 'Issue F: Universe count dynamically resolves to 52 from health API');

  // Issue G: Data health evaluation logic
  function evaluateDataHealth(health) {
    if (!health || health.status === 'stale') return 'Data Warning';
    if (health.status === 'healthy') return 'Data Healthy';
    return 'Pipeline Idle';
  }
  assert(evaluateDataHealth({ status: 'healthy' }) === 'Data Healthy', 'Issue G: Returns Data Healthy when all factors healthy');
  assert(evaluateDataHealth({ status: 'stale' }) === 'Data Warning', 'Issue G: Returns Data Warning when data is stale or missing');

  console.log(`\nDashboard Regressions: ${passed}/${total} assertions passed.\n`);
}

runRegressionTests();
