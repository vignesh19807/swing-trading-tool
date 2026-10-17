/**
 * @file mockStock.js
 * @description Phase 1 & 13 mock data — single stock intelligence report & dynamic lookup.
 *
 * USAGE RULES:
 *   - Only active when VITE_USE_MOCK_DATA=true
 *   - Never used silently in production
 *
 * DATA CONTRACT REFERENCE:
 *   docs/week9_explanation_contract.md
 *   docs/week11_unified_intelligence_contract.md
 *   docs/week16_handoff.md
 */

import { mockOpportunities } from './mockOpportunities.js';
import { mockStocks } from './mockStocks.js';

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
  price_change_percent: 1.45,
  entry_zone_low: 3490.0,
  entry_zone_high: 3545.0,
  stop_loss: 3410.0,
  target: 3720.0,
  risk_reward: 2.1,
  expected_holding_weeks: 5,
  bullish_factors: [
    "RSI showing momentum recovery (RSI 54.2)",
    "Strong EMA alignment (20 > 50 > 200 EMA)",
    "Sector outperforming NIFTY 50 benchmark",
    "Consolidation breakout above weekly pivot",
  ],
  risk_factors: [
    "Elevated volatility (HV20 above 18%)",
    "Approaching quarterly earnings announcement window",
  ],
  explanation: "TCS demonstrates strong technical momentum with multi-timeframe moving average support. The entry zone presents a favourable risk/reward ratio of 2.1:1 with an expected swing horizon of 3–8 weeks.",
};

/**
 * Resolves a mock stock intelligence object for any symbol in the mock dataset.
 * 
 * @param {string} symbol - NSE ticker symbol
 * @returns {object} Stock intelligence payload
 */
export function getMockStock(symbol) {
  if (!symbol) return mockStock;
  const cleanSymbol = String(symbol).toUpperCase().trim();

  // Check if symbol exists in mockOpportunities
  const foundOpp = mockOpportunities.find((o) => o.symbol.toUpperCase() === cleanSymbol);
  if (foundOpp) {
    const isBearish = foundOpp.recommendation === 'SELL' || (foundOpp.stop_loss && foundOpp.target && foundOpp.stop_loss > foundOpp.target);
    return {
      ...mockStock,
      ...foundOpp,
      symbol: foundOpp.symbol,
      company_name: foundOpp.company_name,
      sector: foundOpp.sector,
      industry: foundOpp.industry,
      current_price: foundOpp.current_price,
      price_change_percent: foundOpp.price_change_percent ?? 0.8,
      entry_zone_low: foundOpp.entry_zone_low,
      entry_zone_high: foundOpp.entry_zone_high,
      stop_loss: foundOpp.stop_loss,
      target: foundOpp.target,
      risk_reward: foundOpp.risk_reward,
      expected_holding_weeks: foundOpp.expected_holding_weeks || 5,
      recommendation: foundOpp.recommendation,
      opportunity_score: foundOpp.opportunity_score,
      technical_score: foundOpp.technical_score,
      financial_score: foundOpp.financial_score,
      momentum_score: foundOpp.momentum_score,
      risk_score: foundOpp.risk_score,
      bullish_factors: isBearish ? [
        "Oversold bounce potential near secondary support",
        "Institutional distribution decelerating",
      ] : [
        "Price action consolidating above 50-day EMA",
        "RSI momentum divergence turning positive",
        "Sector relative strength outperforming broader indices",
        "Volume expansion on breakout candle",
      ],
      risk_factors: isBearish ? [
        "Head-and-shoulders breakdown confirmed on daily chart",
        "Key moving averages in death cross formation (50 < 200 EMA)",
        "Weak relative strength versus industry benchmark",
      ] : [
        "Macro resistance cluster within 4% of target",
        "Broader market breadth showing periodic distribution",
      ],
      explanation: isBearish
        ? `${foundOpp.company_name} exhibits distribution patterns with breakdown below key swing support. Downside target is projected with stop-loss strictly placed above structural resistance.`
        : `${foundOpp.company_name} shows constructive swing structure with favorable risk/reward setup. Entry zone allows managed risk positioning with projected target over 3–8 weeks.`,
    };
  }

  // Check if symbol exists in mockStocks (without full opportunity setup)
  const foundStock = mockStocks.find((s) => s.symbol.toUpperCase() === cleanSymbol);
  if (foundStock) {
    return {
      symbol: foundStock.symbol,
      company_name: foundStock.company_name,
      sector: foundStock.sector,
      industry: foundStock.industry,
      current_price: foundStock.current_price,
      price_change_percent: foundStock.change_percent,
      opportunity_score: foundStock.opportunity_score,
      technical_score: 55.0,
      financial_score: 60.0,
      momentum_score: 50.0,
      risk_score: 35.0,
      recommendation: foundStock.recommendation || 'WATCH',
      entry_zone_low: null,
      entry_zone_high: null,
      stop_loss: null,
      target: null,
      risk_reward: null,
      expected_holding_weeks: 5,
      bullish_factors: ["Stable underlying fundamentals", "Normal trading volume"],
      risk_factors: ["Swing setup parameters currently unformed"],
      explanation: `${foundStock.company_name} is under algorithmic tracking. Setup triggers have not yet met criteria for defined entry, stop-loss, and target levels.`,
    };
  }

  // Fallback to default mockStock with the requested symbol
  return {
    ...mockStock,
    symbol: cleanSymbol,
    company_name: `${cleanSymbol} Equities`,
  };
}
