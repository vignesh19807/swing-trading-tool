# Week 9 MONDAY — Explanation Contract

This document defines the schema, data sources, and business rules for the Opportunity Score Explanation Engine.

## 1. Opportunity Score Components

The overall `opportunity_score` (0.0 - 100.0) is mathematically calculated using three weighted sub-scores:

- **Technical Score**: 40% weight
- **Financial Score**: 35% weight
- **Momentum Score**: 25% weight

*Important Note on Momentum:* The Momentum Score is derived directly from the Technical Engine's RSI and MACD sub-scores, resulting in intentional double-counting for momentum characteristics.

## 2. Sector Intelligence (Known Limitation)

**Sector Intelligence currently contributes 0% mathematically to the `opportunity_score`.**
Sector and Industry data evaluated by the `sector_industry_engine` is provided purely as explanatory and contextual information. It does not alter the mathematical value of the final score unless the Decision Engine is explicitly updated in a future approved task.

## 3. Explanation Schema

The Explanation Engine will output the following JSON-compatible structured schema:

```json
{
  "symbol": "string",
  "evaluation_date": "string (YYYY-MM-DD)",
  "opportunity_score": "float",
  "recommendation": "string (BUY | WATCH | HOLD | AVOID | INSUFFICIENT_DATA)",
  "status": "string (VALID | PARTIAL | INSUFFICIENT)",

  "score_breakdown": {
    "technical_score": "float | null",
    "technical_weight": "float",
    "technical_weighted_contribution": "float | null",

    "financial_score": "float | null",
    "financial_weight": "float",
    "financial_weighted_contribution": "float | null",

    "momentum_score": "float | null",
    "momentum_weight": "float",
    "momentum_weighted_contribution": "float | null"
  },

  "explanation": {
    "summary": "string",
    "positive_factors": [
      {
        "category": "string (Technical | Financial | Momentum)",
        "metric": "string",
        "value": "string | float",
        "interpretation": "string"
      }
    ],
    "negative_factors": [
      {
        "category": "string",
        "metric": "string",
        "value": "string | float",
        "interpretation": "string"
      }
    ],
    "neutral_factors": [
      {
        "category": "string",
        "metric": "string",
        "value": "string | float",
        "interpretation": "string"
      }
    ],
    "missing_factors": [
      {
        "category": "string",
        "metric": "string",
        "reason": "string"
      }
    ],
    "sector_context": "string | null"
  }
}
```

## 4. Score Component Mapping & Factor Traceability

All factors are strictly traced to existing read-only outputs from the engines:

- **Technical Score Inputs (`backend/engines/technical_engine.py`)**:
  - RSI Score (Max 30) -> Traced from `rsi_score` and `rsi`
  - MACD Score (Max 30) -> Traced from `macd_score`, `macd`, `signal`, `histogram`
  - Trend Score (Max 20) -> Traced from `trend_score`, `ema20`, `ema50`, `ema200`, `close`
  - Volume Score (Max 20) -> Traced from `volume_score`, `volume`

- **Financial Score Inputs (`backend/engines/financial_engine.py`)**:
  - Profitability Sub-score (40%) -> Traced from `profitability_score` and aggregated `component_statuses`.
  - Growth Sub-score (35%) -> Traced from `growth_score` and aggregated `component_statuses`.
  - Valuation Sub-score (25%) -> Traced from `valuation_score` and aggregated `component_statuses`.
  - *(Note: Raw underlying metrics like ROE, ROCE, and P/E are not exposed upstream and are marked as "Unavailable upstream").*

- **Momentum Score Inputs (`backend/engines/decision_engine.py`)**:
  - Derived from technical `rsi_score` and `macd_score`.

- **Sector Context (`backend/engines/sector_industry_engine.py`)**:
  - Traced from `relative_strength` (vs NIFTY_50) and `preliminary_score`.

## 5. Factor Classification Rules

Factors are categorized into Positive, Negative, or Neutral strictly based on existing engine thresholds. No new rules are invented.

### Financial Classification (Based on existing Logic Analyzers)
- **Valuation**:
  - *Positive*: `valuation_score` > 90.0
  - *Negative*: `valuation_score` <= 60.0
  - *Neutral*: 60.0 < `valuation_score` <= 90.0
- **Profitability**:
  - *Positive*: `profitability_score` > 80.0
  - *Negative*: `profitability_score` <= 40.0
  - *Neutral*: 40.0 < `profitability_score` <= 80.0
- **Growth**:
  - *Positive*: `growth_score` > 80.0
  - *Negative*: `growth_score` <= 50.0
  - *Neutral*: 50.0 < `growth_score` <= 80.0

### Technical Classification (Based on Technical Engine sub-scores)
- **RSI**:
  - *Positive*: `rsi_score` >= 24 (40 <= RSI < 70)
  - *Negative*: `rsi_score` <= 10 (RSI < 30 OR RSI >= 80)
  - *Neutral*: `rsi_score` between 11 and 23
- **MACD**:
  - *Positive*: `macd_score` >= 24 (MACD > Signal AND Histogram > 0)
  - *Negative*: `macd_score` <= 12 (MACD < Signal)
  - *Neutral*: `macd_score` == 15 (Approx equal) OR 20 (MACD > Signal but Hist < 0)
- **Trend/EMA**:
  - *Positive*: `trend_score` >= 15 (Close > EMA20 > EMA50)
  - *Negative*: `trend_score` <= 2 (Close < EMA20 < EMA50)
  - *Neutral*: Mixed alignment (`trend_score` between 5 and 12)
- **Volume**:
  - *Positive*: `volume_score` >= 14 (Ratio >= 1.2x)
  - *Negative*: `volume_score` <= 3 (Ratio < 0.8x)
  - *Neutral*: Ratio 0.8x - 1.2x

### Momentum Classification (Based on Decision Engine derived score)
- **Momentum Composite**:
  - *Positive*: `momentum_score` >= 80.0
  - *Negative*: `momentum_score` <= 40.0
  - *Neutral*: 40.0 < `momentum_score` < 80.0

## 6. Missing-Data Behavior

Missing data is categorized distinctly from negative factors:
- If a specific metric (e.g., MACD) is `NaN` or `None`, it must be placed into the `missing_factors` array with a generated `reason` (e.g., "Insufficient historical quarterly data").
- If a raw metric is not exposed upstream (e.g., raw ROE value from the Financial Engine), its value is marked as "Unavailable upstream".
- The Decision Engine dynamically re-weights component scores if Momentum is missing (Tech: 53.33%, Fin: 46.66%). If this occurs, the `score_breakdown` weights must accurately reflect this dynamic adjustment.
- If the `status` of the overall analysis is `INSUFFICIENT`, the final `opportunity_score` is `null`. The Explanation Engine will simply explain that calculation was aborted due to lack of minimum mandatory data.

## 7. Evaluation-Date Behavior and Historical Determinism

The `evaluation_date` is a first-class citizen of the contract.
- All data fed into the Explanation Engine must correspond exactly to the data snapshot available on the `evaluation_date`.
- The Explanation Engine must not perform any historical data fetching; it only processes the snapshots passed to it by the existing engines.
- This guarantees historical determinism: generating an explanation for "2024-05-20" today will yield the exact same explanation logic as it would have on that date, preventing future-leakage.

## 8. Sample Structured Output

```json
{
  "symbol": "TCS",
  "evaluation_date": "2024-05-20",
  "opportunity_score": 78.50,
  "recommendation": "BUY",
  "status": "VALID",
  "score_breakdown": {
    "technical_score": 82.5,
    "technical_weight": 0.40,
    "technical_weighted_contribution": 33.0,
    "financial_score": 85.0,
    "financial_weight": 0.35,
    "financial_weighted_contribution": 29.75,
    "momentum_score": 63.0,
    "momentum_weight": 0.25,
    "momentum_weighted_contribution": 15.75
  },
  "explanation": {
    "summary": "TCS generates a BUY recommendation driven by high profitability (ROE, ROCE) and strong technical uptrend, offsetting a premium valuation.",
    "positive_factors": [
      {
        "category": "Financial",
        "metric": "Profitability",
        "value": "Score: 90.00/100",
        "interpretation": "Strong profitability metrics (e.g., high ROE, ROCE, or Net Margin)."
      },
      {
        "category": "Technical",
        "metric": "Trend",
        "value": "Close > EMA20 > EMA50",
        "interpretation": "Strong short-term and medium-term bullish trend alignment."
      }
    ],
    "negative_factors": [
      {
        "category": "Financial",
        "metric": "Valuation",
        "value": "Score: 35.00/100",
        "interpretation": "Overvalued or Unprofitable."
      }
    ],
    "neutral_factors": [
      {
        "category": "Technical",
        "metric": "RSI",
        "value": "62",
        "interpretation": "Momentum is slightly elevated but remains in the neutral zone."
      }
    ],
    "missing_factors": [],
    "sector_context": "IT Sector is currently ranked #2, exhibiting strong 63D relative strength (+5.2%) against the NIFTY_50 benchmark."
  }
}
```
