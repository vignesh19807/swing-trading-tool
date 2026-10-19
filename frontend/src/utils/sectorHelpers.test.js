/**
 * @file sectorHelpers.test.js
 * @description Unit tests for sector normalization, classification, filtering, and sorting.
 */

import {
  normalizeSectorData,
  filterSectors,
  sortSectors,
  calculateSectorSummary
} from './sectorHelpers.js';

let passed = 0;
let failed = 0;

function assert(condition, message) {
  if (!condition) {
    console.error(`❌ FAIL: ${message}`);
    failed++;
    throw new Error(message);
  } else {
    console.log(`✅ PASS: ${message}`);
    passed++;
  }
}

function assertCloseTo(actual, expected, tolerance = 0.01, message) {
  const diff = Math.abs(actual - expected);
  if (diff > tolerance) {
    console.error(`❌ FAIL: ${message} (Expected: ${expected}, Got: ${actual}, Diff: ${diff})`);
    failed++;
    throw new Error(message);
  } else {
    console.log(`✅ PASS: ${message}`);
    passed++;
  }
}

console.log('\n--- Testing Sector Normalization (Mock Format) ---');

const mockIT = {
  sector: "Information Technology",
  performance_21d: 3.2,
  performance_63d: 8.5,
  performance_126d: 12.1,
  relative_strength_vs_nifty: 1.08,
  stock_count: 8,
};

const normalizedMockIT = normalizeSectorData(mockIT, 0);
assert(normalizedMockIT.name === 'Information Technology', 'Correctly extracts mock sector name');
assert(normalizedMockIT.rank === 1, 'Assigns rank 1');
assert(normalizedMockIT.performance_21d === 3.2, 'Extracts 21d performance as 3.2%');
assert(normalizedMockIT.performance_63d === 8.5, 'Extracts 63d performance as 8.5%');
assert(normalizedMockIT.performance_126d === 12.1, 'Extracts 126d performance as 12.1%');
assert(normalizedMockIT.relativeStrength === 1.08, 'Extracts relative strength ratio as 1.08');
assert(normalizedMockIT.relativeStrengthType === 'ratio', 'Identifies relative strength type as ratio');
assert(normalizedMockIT.relativeStrengthStatus === 'VALID', 'Marks valid relative strength');
assert(normalizedMockIT.status === 'Outperforming', 'Classifies RS 1.08 as Outperforming');
assert(normalizedMockIT.stockCount === 8, 'Extracts stock count as 8');

const mockBanking = {
  sector: "Banking",
  performance_21d: -1.1,
  performance_63d: 4.2,
  performance_126d: 6.8,
  relative_strength_vs_nifty: 0.94,
  stock_count: 6,
};

const normalizedMockBanking = normalizeSectorData(mockBanking, 1);
assert(normalizedMockBanking.status === 'Lagging', 'Classifies RS 0.94 as Lagging');
assert(normalizedMockBanking.performance_21d === -1.1, 'Preserves negative return -1.1%');

const mockEnergy = {
  sector: "Energy",
  performance_21d: 1.5,
  performance_63d: 5.0,
  performance_126d: 9.3,
  relative_strength_vs_nifty: 1.02,
  stock_count: 4,
};

const normalizedMockEnergy = normalizeSectorData(mockEnergy, 2);
assert(normalizedMockEnergy.status === 'In-line', 'Classifies RS 1.02 as In-line');

console.log('\n--- Testing Sector Normalization (Backend Engine Schema) ---');

const backendEngineSector = {
  rank: 1,
  sector: "Capital Goods",
  performance: {
    "21D": 0.045,
    "63D": 0.082,
    "126D": 0.154,
  },
  relative_strength: {
    benchmark: "NIFTY_50",
    "63D_rs": 0.027,
    status: "VALID",
  },
  preliminary_score: {
    score: 72.5,
  },
  constituents_count: 10,
  constituents: ["LT", "SIEMENS", "ABB"],
  data_quality: "VALID",
};

const normalizedBackend = normalizeSectorData(backendEngineSector, 0);
assert(normalizedBackend.name === 'Capital Goods', 'Extracts name from backend contract');
assertCloseTo(normalizedBackend.performance_21d, 4.5, 0.01, 'Converts 21D decimal 0.045 to 4.5%');
assertCloseTo(normalizedBackend.performance_63d, 8.2, 0.01, 'Converts 63D decimal 0.082 to 8.2%');
assertCloseTo(normalizedBackend.performance_126d, 15.4, 0.01, 'Converts 126D decimal 0.154 to 15.4%');
assert(normalizedBackend.relativeStrength === 0.027, 'Extracts difference-based relative strength');
assert(normalizedBackend.relativeStrengthType === 'difference', 'Identifies relative strength type as difference');
assert(normalizedBackend.status === 'Outperforming', 'Classifies difference +0.027 as Outperforming');
assert(normalizedBackend.stockCount === 10, 'Extracts constituents_count 10');
assert(normalizedBackend.score === 72.5, 'Extracts preliminary score');
assert(Array.isArray(normalizedBackend.constituentsList), 'Preserves constituents array');
assert(normalizedBackend.constituentsList.length === 3, 'Contains 3 constituent symbols');

console.log('\n--- Testing Missing / Unavailable Benchmark Data (No Fake Data) ---');

const backendUnavailableRS = {
  sector: "Pharmaceuticals",
  performance: {
    "21D": 0.012,
    "63D": 0.035,
  },
  relative_strength: {
    benchmark: "NIFTY_50",
    status: "UNAVAILABLE",
    "21D_rs": null,
    "63D_rs": null,
    warning: "Benchmark historical data service is not currently available.",
  },
  constituents_count: 5,
};

const normalizedUnavailable = normalizeSectorData(backendUnavailableRS, 3);
assert(normalizedUnavailable.relativeStrength === null, 'Relative strength remains null when unavailable');
assert(normalizedUnavailable.relativeStrengthStatus === 'UNAVAILABLE', 'Status marked as UNAVAILABLE');

console.log('\n--- Testing Corrupted / Null Input Resilience ---');

const nullSector = normalizeSectorData(null, 4);
assert(nullSector.name === 'Sector 5', 'Safely defaults name for null input');
assert(nullSector.performance_21d === null, 'Null input yields null 21d performance');
assert(nullSector.relativeStrength === null, 'Null input yields null relative strength');

console.log('\n--- Testing Sector Filtering ---');

const sectors = [normalizedMockIT, normalizedMockBanking, normalizedMockEnergy];
const stocksBySector = {
  'information technology': [{ symbol: 'TCS', company_name: 'Tata Consultancy Services' }],
  'banking': [{ symbol: 'HDFCBANK', company_name: 'HDFC Bank' }],
  'energy': [{ symbol: 'RELIANCE', company_name: 'Reliance Industries' }],
};

const searchFiltered = filterSectors(sectors, { searchQuery: 'Bank', statusFilter: 'ALL', stocksBySector });
assert(searchFiltered.length === 1, 'Search query "Bank" matches Banking sector');
assert(searchFiltered[0].name === 'Banking', 'Matched sector is Banking');

const constituentSearch = filterSectors(sectors, { searchQuery: 'TCS', statusFilter: 'ALL', stocksBySector });
assert(constituentSearch.length === 1, 'Search query matches constituent stock symbol TCS');
assert(constituentSearch[0].name === 'Information Technology', 'Constituent search returns Information Technology');

const outperformingFiltered = filterSectors(sectors, { searchQuery: '', statusFilter: 'Outperforming', stocksBySector });
assert(outperformingFiltered.length === 1, 'Filtered 1 Outperforming sector');
assert(outperformingFiltered[0].name === 'Information Technology', 'Outperforming sector is Information Technology');

const laggingFiltered = filterSectors(sectors, { searchQuery: '', statusFilter: 'Lagging', stocksBySector });
assert(laggingFiltered.length === 1, 'Filtered 1 Lagging sector');
assert(laggingFiltered[0].name === 'Banking', 'Lagging sector is Banking');

const allFiltered = filterSectors(sectors, { searchQuery: '', statusFilter: 'ALL', stocksBySector });
assert(allFiltered.length === 3, 'Status ALL returns all 3 sectors');

console.log('\n--- Testing Sector Sorting ---');

const sortedDesc = sortSectors(sectors, 'performance-desc', '63d');
assert(sortedDesc[0].name === 'Information Technology', 'Highest 63d return is IT (8.5%)');
assert(sortedDesc[1].name === 'Energy', 'Second 63d return is Energy (5.0%)');
assert(sortedDesc[2].name === 'Banking', 'Third 63d return is Banking (4.2%)');

const sortedAsc = sortSectors(sectors, 'performance-asc', '63d');
assert(sortedAsc[0].name === 'Banking', 'Lowest 63d return is Banking (4.2%)');

const sortedAlpha = sortSectors(sectors, 'name-asc');
assert(sortedAlpha[0].name === 'Banking', 'Alphabetical first is Banking');
assert(sortedAlpha[1].name === 'Energy', 'Alphabetical second is Energy');
assert(sortedAlpha[2].name === 'Information Technology', 'Alphabetical third is Information Technology');

const sortedCount = sortSectors(sectors, 'stocks-desc');
assert(sortedCount[0].stockCount === 8, 'Most stocks is IT with 8');
assert(sortedCount[1].stockCount === 6, 'Second most stocks is Banking with 6');
assert(sortedCount[2].stockCount === 4, 'Third most stocks is Energy with 4');

console.log('\n--- Testing Sector Summary Statistics ---');

const summary = calculateSectorSummary(sectors);
assert(summary.total === 3, 'Total sectors is 3');
assert(summary.outperforming === 1, 'Outperforming sectors count is 1');
assert(summary.lagging === 1, 'Lagging sectors count is 1');
assert(summary.inLine === 1, 'In-line sectors count is 1');
assert(summary.topSector.name === 'Information Technology', 'Top sector is Information Technology');
assert(summary.topReturn === 8.5, 'Top return is 8.5%');

const emptySummary = calculateSectorSummary([]);
assert(emptySummary.total === 0, 'Empty sectors list yields total 0');
assert(emptySummary.topSector === null, 'Empty sectors list yields null topSector');

console.log(`\n🎉 All ${passed} sector helper tests passed successfully (${passed} passed, ${failed} failed).\n`);
