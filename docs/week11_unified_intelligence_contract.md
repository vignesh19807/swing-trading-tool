# Week 11 Unified Stock Intelligence & Handoff Contract

## 1. Purpose
This document specifies the unified data boundary and API handoff contract for Week 11 of the Swing Trading Tool. It defines how the Data Engineer's **Unified Stock Snapshot Service** integrates into the Logic Engineer's engines, and details the API-ready **Structured Stock Intelligence** output.

---

## 2. Team Boundaries & System Ownership

### Data Engineer Ownership
- `backend/data_pipeline/stock_snapshot_service.py`
- `backend/data_pipeline/data_service.py`
- `backend/data_pipeline/financial_service.py`
- `backend/data_pipeline/classification_service.py`
- `backend/data_pipeline/stop_target_input_service.py`
- SQLite database tables (`daily_price`, `financial_statements`, `company_classification`, etc.)

### Logic Engineer Ownership
- `backend/logic/stock_intelligence.py` (Structured Stock Intelligence Assembly)
- `backend/engines/decision_engine.py` (Composite Opportunity Score V1)
- `backend/engines/technical_engine.py` (Technical Analysis Pipeline)
- `backend/engines/financial_engine.py` (Financial Health Aggregator)
- `backend/engines/ranking_engine.py` (Universe Top 10 Ranking Engine)
- `backend/engines/universe_orchestrator.py` (End-to-End Orchestrator)
- `backend/logic/signal_engine.py` & `signal_integration.py` (Signal Generation)
- `backend/logic/trade_quality_engine.py` (Trade Quality & Risk Context)
- `backend/logic/explanation/` (Opportunity Explanation Engine)

---

## 3. Data Engineer Unified Stock Snapshot Contract

Function interface:
```python
get_stock_snapshot(symbol: str, evaluation_date: Optional[str] = None) -> Dict[str, Any]
```

### Supported Snapshot Fields
- `symbol` (`str`): Cleaned NSE ticker symbol (e.g. `"TCS"`).
- `status` (`str`): `"VALID"` | `"PARTIAL"` | `"INCOMPLETE"` | `"INVALID"`.
- `identity` (`dict` | `None`): Classification details (`symbol`, `company_name`, `sector`, `industry`).
- `market` (`dict` | `None`): Latest available single EOD market price bar (`open`, `high`, `low`, `close`, `volume`, `date`).
- `financial` (`dict` | `None`): Latest available single financial record (`revenue`, `net_profit`, `eps`, `roe`, `roce`, `debt_equity`, `operating_margin`, `net_margin`).
- `data_quality` (`dict`): Completeness status, warnings, missing financial fields list.
- `source` (`dict`): Traceability mapping for component data services.

> **CRITICAL NOTE ON SNAPSHOT CONTENT**:
> The Unified Stock Snapshot contains **only a single market record and a single latest financial record**. It **does NOT** contain full historical OHLCV series (500 days) or multi-quarter financial histories.
> 
> Therefore, historical engines (Technical Engine, Financial Engine) MUST continue retrieving their required historical series through approved data services (`get_stock_data`, `analyze_financial_health`).

---

## 4. Historical `evaluation_date` Propagation & Point-in-Time Safety

- When `evaluation_date` (format: `YYYY-MM-DD`) is supplied, it is forwarded consistently to every underlying service:
  - `get_stock_snapshot(symbol, evaluation_date=evaluation_date)`
  - `get_stock_data(symbol, end_date=evaluation_date)`
  - `analyze_financial_health(symbol, evaluation_date=evaluation_date)`
  - `get_stock_sector_performance_context(symbol, evaluation_date=evaluation_date)`
  - `run_signal_pipeline(symbol, evaluation_date=evaluation_date)`
  - `explain_opportunity(..., evaluation_date=evaluation_date)`
- All data lookup is restricted to records at or before `evaluation_date`, preventing lookahead/future data leakage.

---

## 5. Engine Input Mapping & Context Flow

```text
Unified Stock Snapshot
       │
       ├─► Identity / Data Quality Context
       │
       ├─► Existing Historical Data Services (Point-in-time)
       │         │
       │         ├─► Technical Engine (Historical OHLCV)
       │         ├─► Financial Engine (Historical Financials)
       │         └─► Sector Engine (Classification + Benchmark History)
       │
       └─► Decision Engine ──► Signal Engine ──► Trade Quality ──► Explanation
                                                                       │
                                                                       ▼
                                                          Structured Stock Intelligence
```

---

## 6. Structured Stock Intelligence Output Schema

Function interface:
```python
get_stock_intelligence(symbol: str, evaluation_date: Optional[str] = None) -> Dict[str, Any]
```

### Public Field Specifications
1. `symbol` (`str`): Ticker symbol.
2. `evaluation_date` (`str` | `None`): Target historical date.
3. `status` (`str`): Overall validity status (`"VALID"`, `"PARTIAL"`, `"INSUFFICIENT"`, `"INVALID"`).
4. `identity` (`dict` | `None`): Company classification metadata.
5. `data_quality` (`dict` | `None`): Data completeness warnings and missing field lists.
6. `technical_intelligence` (`dict` | `None`): Technical score & indicator summaries (RSI, MACD, Trend, Volume).
7. `financial_intelligence` (`dict` | `None`): Financial score & sub-scores (Profitability, Growth, Valuation, completeness).
8. `sector_intelligence` (`dict` | `None`): Sector classification, stock/sector performance, preliminary sector score.
9. `decision_result` (`dict`): Composite Opportunity Score (0-100), Recommendation (`BUY`, `WATCH`, `HOLD`, `AVOID`, `INSUFFICIENT_DATA`), technical/financial/momentum subscores.
10. `signal_result` (`dict` | `None`): Signal validity, entry price zone (`entry_lower`, `entry_upper`), stop loss, target, risk, reward, risk/reward ratio.
11. `trade_quality` (`dict` | `None`): Additive eligibility status (`"ELIGIBLE"`, `"INELIGIBLE"`, `"INVALID"`, `"INCOMPLETE"`), risk flags, eligibility reason.
12. `structured_explanation` (`dict` | `None`): Score breakdown weights/contributions, positive/negative/neutral/missing factor interpretations, sector context.

---

## 7. Error Handling & Missing Data Behavior

- **Snapshot Failure**: Handled defensively. Scoring and engine calculations proceed using existing historical data pipelines without crashing.
- **Missing Financial/Technical Core Data**: Decision Engine returns `status: "INSUFFICIENT"`, `opportunity_score: None`, `recommendation: "INSUFFICIENT_DATA"`.
- **Missing Sector Intelligence**: Falls back gracefully to neutral sector score without degrading Opportunity Score calculations.
- **Signal Engine Failure / Non-BUY Recommendation**: Generates `signal_valid: False` with explicit reason (`"NOT_A_BUY_RECOMMENDATION"`, `"MISSING_OR_INVALID_INPUTS"`, etc.).
- **Trade Quality Context**: Additive only; marked as `"INELIGIBLE"` or `"INCOMPLETE"` without altering ranking order or Opportunity Scores.

---

## 8. Determinism Expectations
- Given identical inputs (`symbol` and `evaluation_date`), `get_stock_intelligence()` produces mathematically identical, key-order-stable dictionary payloads.
- Floating point values are rounded to 4 decimal places where applicable.
- All non-standard numeric primitives (`NaN`, `Inf`) are sanitized to `None` for JSON compliance.

---

## 9. API-Ready JSON Example

```json
{
  "symbol": "TCS",
  "evaluation_date": "2026-08-14",
  "status": "PARTIAL",
  "identity": {
    "symbol": "TCS",
    "company_name": "Tata Consultancy Services Limited",
    "sector": "Information Technology",
    "industry": "IT Services"
  },
  "data_quality": {
    "status": "PARTIAL",
    "warnings": ["Missing financial fields: roce"],
    "financial_missing_fields": ["roce"]
  },
  "technical_intelligence": {
    "technical_score": 56.0,
    "rsi_score": 30.0,
    "macd_score": 8.0,
    "trend_score": 15.0,
    "volume_score": 3.0
  },
  "financial_intelligence": {
    "status": "PARTIAL",
    "overall_score": 82.0358,
    "profitability_score": 92.4554,
    "growth_score": 68.548,
    "valuation_score": 84.2475,
    "component_statuses": {
      "roe": "VALID",
      "roce": "PARTIAL",
      "debt_equity": "VALID",
      "profit_margin": "VALID",
      "growth": "PARTIAL",
      "volatility": "VALID",
      "valuation": "PARTIAL"
    },
    "data_completeness": 0.5714
  },
  "sector_intelligence": {
    "symbol": "TCS",
    "evaluation_date": "2026-08-14",
    "status": "VALID",
    "classification": {
      "company_name": "Tata Consultancy Services Limited",
      "sector": "Information Technology",
      "industry": "IT Services"
    },
    "stock_performance": {"21D": 0.0727, "63D": 0.034, "126D": -0.1251, "252D": -0.1913},
    "sector_performance": {
      "data_quality": "VALID",
      "performance": {"21D": 0.0876, "63D": 0.0585, "126D": -0.075, "252D": -0.0908},
      "preliminary_score": {"score": 64.607, "components": {"base": 50.0, "21D_component": 8.7618, "63D_component": 5.8452}}
    }
  },
  "decision_result": {
    "symbol": "TCS",
    "status": "PARTIAL",
    "technical_score": 56.0,
    "financial_score": 82.0358,
    "momentum_score": 63.3333,
    "opportunity_score": 66.9459,
    "recommendation": "WATCH"
  },
  "signal_result": {
    "signal_valid": false,
    "entry_lower": 2354.2333,
    "entry_upper": 2387.8869,
    "stop_loss": null,
    "target": null,
    "risk": null,
    "reward": null,
    "risk_reward_ratio": null,
    "reason": "NOT_A_BUY_RECOMMENDATION",
    "symbol": "TCS",
    "evaluation_date": "2026-08-14",
    "recommendation": "WATCH",
    "trade_quality": {
      "is_eligible": false,
      "risk_status": "INELIGIBLE",
      "eligibility_reason": "NOT_A_BUY_RECOMMENDATION",
      "risk_flags": ["NON_BUY_RECOMMENDATION"]
    },
    "is_eligible": false
  },
  "trade_quality": {
    "is_eligible": false,
    "risk_status": "INELIGIBLE",
    "eligibility_reason": "NOT_A_BUY_RECOMMENDATION",
    "risk_flags": ["NON_BUY_RECOMMENDATION"]
  },
  "structured_explanation": {
    "symbol": "TCS",
    "evaluation_date": "2026-08-14",
    "opportunity_score": 66.9459,
    "recommendation": "WATCH",
    "status": "PARTIAL",
    "score_breakdown": {
      "technical_score": 56.0,
      "technical_weight": 0.4,
      "technical_weighted_contribution": 22.4,
      "financial_score": 82.0358,
      "financial_weight": 0.35,
      "financial_weighted_contribution": 28.7125,
      "momentum_score": 63.3333,
      "momentum_weight": 0.25,
      "momentum_weighted_contribution": 15.8333
    },
    "explanation": {
      "summary": "TCS is placed on WATCH due to a balanced mix of positive and cautionary factors.",
      "positive_factors": [
        {"category": "Technical", "metric": "RSI", "value": "52.92", "interpretation": "RSI is in a strong momentum zone (40-70)."},
        {"category": "Financial", "metric": "Profitability", "value": "Score: 92.46/100", "interpretation": "Strong profitability metrics."}
      ],
      "negative_factors": [
        {"category": "Technical", "metric": "MACD", "value": "MACD: 49.88, Signal: 59.91", "interpretation": "MACD line is below Signal line."}
      ],
      "neutral_factors": [],
      "missing_factors": []
    }
  }
}
```

---

## 10. Internal Fields That Must NOT Be Exposed
The public API output MUST NOT contain:
- `_explanation_context`
- Raw `pandas.DataFrame` objects (e.g. `indicators_df`, `historical_prices`)
- Direct SQL handles, cursor objects, or connection strings
- Python exception tracebacks
- Intermediate transient arrays

---

## 11. Dependencies Between Data and Logic Layers
- **Data Layer Dependencies**: Logic layer depends on `stock_snapshot_service.get_stock_snapshot` for validated metadata, `data_service.get_stock_data` for historical price series, `financial_service.get_latest_financial_data` for statements, and `stop_target_input_service.get_stop_target_inputs` for price geometry.
- **Logic Layer Independence**: All scoring, momentum derivation, opportunity score calculation, signal generation, trade quality flags, and structured explanation synthesis are computed strictly within Logic components.
