/**
 * @file mockOpportunities.js
 * @description Phase 1 mock data — ranked swing opportunities.
 *
 * USAGE RULES:
 *   - This file must only be used when VITE_USE_MOCK_DATA=true
 *   - Mock data must NEVER silently replace failed API requests in production
 *   - This file is for offline development and component testing ONLY
 *   - Production screens must use real backend responses
 *
 * DATA CONTRACT REFERENCE:
 *   docs/week11_unified_intelligence_contract.md
 *   docs/week16_handoff.md
 *
 * Phase 1 NOTE:
 *   This contains minimal placeholder records only.
 *   A full mock dataset will be added in Phase 2/3 once the API schema
 *   is confirmed with the backend team.
 */

export const mockOpportunities = [
  {
    symbol: "TCS",
    company_name: "Tata Consultancy Services Ltd",
    sector: "Information Technology",
    industry: "IT Services & Consulting",
    opportunity_score: 78.5,
    technical_score: 80.2,
    financial_score: 76.1,
    momentum_score: 79.0,
    risk_score: 22.0,
    recommendation: "BUY",
    current_price: 3520.0,
    entry_zone_low: 3490.0,
    entry_zone_high: 3545.0,
    stop_loss: 3410.0,
    target: 3720.0,
    risk_reward: 2.1,
    expected_holding_weeks: 5,
  },
  {
    symbol: "WIPRO",
    company_name: "Wipro Ltd",
    sector: "Information Technology",
    industry: "IT Services & Consulting",
    opportunity_score: 64.3,
    technical_score: 62.0,
    financial_score: 67.4,
    momentum_score: 63.5,
    risk_score: 35.0,
    recommendation: "WATCH",
    current_price: 480.5,
    entry_zone_low: 472.0,
    entry_zone_high: 488.0,
    stop_loss: 455.0,
    target: 520.0,
    risk_reward: 1.7,
    expected_holding_weeks: 6,
  },
];
