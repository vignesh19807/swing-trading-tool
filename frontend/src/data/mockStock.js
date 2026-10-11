/**
 * @file mockStock.js
 * @description Phase 1 mock data — single stock intelligence report.
 *
 * USAGE RULES:
 *   - Only active when VITE_USE_MOCK_DATA=true
 *   - Never used silently in production
 *
 * DATA CONTRACT REFERENCE:
 *   docs/week9_explanation_contract.md
 *   docs/week16_handoff.md (Section 2 — Logic Engine Contract Specifications)
 *
 * Phase 1 NOTE:
 *   Minimal placeholder only. Full mock dataset added in later phases.
 */

export const mockStock = {
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
  bullish_factors: [
    "RSI showing momentum recovery",
    "Strong EMA alignment (20 > 50 > 200)",
    "Sector outperforming NIFTY 50",
  ],
  risk_factors: [
    "Elevated volatility (HV20)",
    "Near resistance zone",
  ],
  explanation: "TCS shows strong technical momentum supported by fundamentals. Entry zone presents a favourable risk/reward of 2.1:1.",
};
