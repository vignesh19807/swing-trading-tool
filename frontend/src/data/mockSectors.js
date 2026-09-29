/**
 * @file mockSectors.js
 * @description Phase 1 mock data — sector and industry performance summary.
 *
 * USAGE RULES:
 *   - Only active when VITE_USE_MOCK_DATA=true
 *   - Never used silently in production
 *
 * Phase 1 NOTE:
 *   Minimal placeholder only.
 */

export const mockSectors = [
  {
    sector: "Information Technology",
    performance_21d: 3.2,
    performance_63d: 8.5,
    performance_126d: 12.1,
    relative_strength_vs_nifty: 1.08,
    stock_count: 8,
  },
  {
    sector: "Banking",
    performance_21d: -1.1,
    performance_63d: 4.2,
    performance_126d: 6.8,
    relative_strength_vs_nifty: 0.94,
    stock_count: 6,
  },
  {
    sector: "Energy",
    performance_21d: 1.5,
    performance_63d: 5.0,
    performance_126d: 9.3,
    relative_strength_vs_nifty: 1.02,
    stock_count: 4,
  },
];
