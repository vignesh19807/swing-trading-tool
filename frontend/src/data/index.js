/**
 * @file index.js
 * @description Data directory documentation file.
 *
 * This directory contains MOCK DATA for offline/test development ONLY.
 *
 * MOCK DATA RULES (enforced by architecture):
 *   1. Mock data lives ONLY in this directory (src/data/).
 *   2. Mock data is ONLY loaded when VITE_USE_MOCK_DATA=true.
 *   3. Mock data must NEVER silently replace failed API requests.
 *   4. Production screens must use real backend responses.
 *   5. Do not create large synthetic datasets here; keep mocks minimal.
 *
 * FILES:
 *   mockOpportunities.js  — ranked swing opportunity list (minimal Phase 1)
 *   mockStocks.js         — stock universe list (minimal Phase 1)
 *   mockStock.js          — single stock intelligence report (minimal Phase 1)
 *   mockSectors.js        — sector performance summary (minimal Phase 1)
 *
 * HOW TO ENABLE MOCK DATA:
 *   In your .env.local:
 *     VITE_USE_MOCK_DATA=true
 *
 * DATA CONTRACT REFERENCES:
 *   docs/week9_explanation_contract.md
 *   docs/week11_unified_intelligence_contract.md
 *   docs/week16_handoff.md
 */
