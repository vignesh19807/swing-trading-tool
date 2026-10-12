# Frontend API Contract & Integration Planning

**Document Version**: 1.0.0 (Phase 9)
**Created**: 2026-10-11
**Last Updated**: 2026-10-11
**Status**: DRAFT — Pending Backend Team Review

---

## 1. Purpose & Scope

This document defines the API contract between the **React frontend** and the **Python backend** for the Swing Trading Intelligence Platform. It serves three purposes:

1. **Contract definition** — Every endpoint the frontend expects, with request/response schemas.
2. **Verification audit** — Clearly labelling what the backend already implements vs. what must be built.
3. **Integration checklist** — What must be confirmed before the frontend can switch from mock data to real API calls.

### Audience
- Frontend developers integrating real API calls
- Backend developers building the REST API layer
- QA verifying contract compliance

### Key Terminology

| Term | Meaning |
|:--|:--|
| **IMPLEMENTED** | Backend logic exists and is verified. Only needs an HTTP route to expose it. |
| **PARTIALLY IMPLEMENTED** | Backend logic exists for part of the feature; the route or some fields are missing. |
| **PROPOSED** | No backend implementation exists. Schema is a frontend proposal requiring backend agreement. |

---

## 2. Current Backend Endpoint Audit

### 2.1 Backend API Layer Status

The backend has a rich **logic and engine layer** with verified, tested code:

| Backend Module | Status | Test Coverage |
|:--|:--|:--|
| `engines/decision_engine.py` | Verified (330/330 tests) | Composite Opportunity Score (0-100) |
| `engines/ranking_engine.py` | Verified | Top 10 universe ranking |
| `engines/universe_orchestrator.py` | Verified | End-to-end universe sweep |
| `engines/technical_engine.py` | Verified | RSI, EMA, MACD, ATR, volatility |
| `engines/financial_engine.py` | Verified | ROE, ROCE, D/E, margins, growth, valuation |
| `engines/sector_industry_engine.py` | Verified | Sector and industry rankings |
| `logic/stock_intelligence.py` | Verified | Full stock intelligence payload |
| `logic/signal_engine.py` | Verified | Entry zone, stop loss, target calculations |
| `logic/trade_quality_engine.py` | Verified | Trade eligibility and risk flags |
| `logic/backtest_engine.py` | Verified | Historical backtesting |
| `logic/backtest_metrics.py` | Verified | Win rate, profit factor, drawdown |
| `logic/explanation/` | Verified | Structured opportunity explanations |

**However, the backend has NO HTTP/REST API layer.**

- `backend/app.py` is **empty** (0 bytes of code).
- `backend/api/` contains only a `.gitkeep` file.
- `backend/models/` contains only a `.gitkeep` file.
- No Flask, FastAPI, or Django app is configured.
- No route definitions, request handlers, serializers, or middleware exist.

> **Critical Finding**: The backend's logic engines are fully functional Python modules that can be called directly, but there are **zero HTTP endpoints** for the frontend to consume. The entire REST API layer must be built by the backend team.

### 2.2 Database Status

From `docs/week15_data_health_report.md`:
- **50 companies** in universe, 16 sectors, 32 industries
- **25,495 daily price rows** (2024-08-14 to 2026-08-28)
- **25,495 technical indicator rows** (1:1 sync with prices)
- **280 quarterly financial records** (2024-12-31 to 2026-06-30)
- Database: SQLite at `database/swing_trading.db`

---

## 3. Endpoint-by-Endpoint Contract

### 3.1 GET /api/market/indices — Market Overview

| Attribute | Value |
|:--|:--|
| **Verification Status** | **PROPOSED** — No backend implementation exists for market index data. The backend database stores individual stock data for a 50-stock universe, not index-level data (NIFTY 50, SENSEX). |
| **Frontend Service Function** | `getMarketIndices()` in `frontend/src/services/api.js` |
| **Mock Data File** | `frontend/src/data/mockMarket.js` |
| **Consumed By** | `Dashboard.jsx` — Top metric cards (NIFTY 50, SENSEX, Market Condition) |

**Proposed Request**
```
GET /api/market/indices
```
No query parameters.

**Proposed Response Schema**

> WARNING: This schema is a frontend proposal. The backend does not currently store or compute index-level data.

```json
{
  "nifty50": {
    "value": 25412.30,
    "change_percent": 0.72,
    "is_positive": true
  },
  "sensex": {
    "value": 83450.22,
    "change_percent": 0.58,
    "is_positive": true
  },
  "condition": {
    "status": "Positive",
    "label": "Swing friendly",
    "description": "Breadth improving",
    "advancing": 1248,
    "declining": 724
  }
}
```

**Required/Optional Fields**

| Field | Type | Required | Notes |
|:--|:--|:--|:--|
| `nifty50.value` | `number` | Required | Latest index value |
| `nifty50.change_percent` | `number` | Required | Daily change percentage |
| `nifty50.is_positive` | `boolean` | Required | Whether change is positive |
| `sensex.value` | `number` | Required | Latest index value |
| `sensex.change_percent` | `number` | Required | Daily change percentage |
| `sensex.is_positive` | `boolean` | Required | Whether change is positive |
| `condition.status` | `string` | Required | Enum: `"Positive"`, `"Neutral"`, `"Negative"` |
| `condition.label` | `string` | Required | Human-readable label |
| `condition.description` | `string` | Required | Short description |
| `condition.advancing` | `integer` | Required | Count of advancing stocks |
| `condition.declining` | `integer` | Required | Count of declining stocks |

**Frontend State Handling**
- **Loading**: `<LoadingState />` spinner while fetching
- **Error**: `<ErrorState />` with retry button; error message displayed to user
- **Empty/Null**: Dashboard guards with `{indices && (...)}` — if null, cards are hidden
- **Partial**: Frontend assumes all fields are present if the top-level object is not null

**Backend Team Questions**
1. Does the backend team plan to source NIFTY 50 / SENSEX data? The current database has only individual stock prices.
2. How will market breadth (advancing/declining) be calculated? From the 50-stock universe or NSE-wide data?
3. What is the data refresh frequency for index values?

---

### 3.2 GET /api/opportunities — Swing Trading Opportunities

| Attribute | Value |
|:--|:--|
| **Verification Status** | **IMPLEMENTED (Logic Only)** — `universe_orchestrator.rank_universe()` and `get_universe_stock_intelligence()` produce complete ranked opportunity data. No HTTP route exists. |
| **Frontend Service Function** | `getOpportunities()` in `frontend/src/services/api.js` |
| **Mock Data File** | `frontend/src/data/mockOpportunities.js` |
| **Backend Source** | `universe_orchestrator.rank_universe()` and `ranking_engine.generate_top_10_ranking()` |
| **Consumed By** | `Dashboard.jsx` via `OpportunityTable` component |

**Request**
```
GET /api/opportunities
```
No query parameters (returns the top-ranked opportunities).

**Response Schema** (verified backend fields + proposed frontend fields)

```json
[
  {
    "symbol": "TCS",
    "company_name": "Tata Consultancy Services Limited",
    "sector": "Information Technology",
    "industry": "IT Services",
    "opportunity_score": 78.5,
    "technical_score": 80.2,
    "financial_score": 76.1,
    "momentum_score": 79.0,
    "risk_score": 22.0,
    "recommendation": "BUY",
    "current_price": 3520.0,
    "entry_zone_low": 3490.0,
    "entry_zone_high": 3545.0,
    "stop_loss": 3410.0,
    "target": 3720.0,
    "risk_reward": 2.1,
    "expected_holding_weeks": 5,
    "rank": 1,
    "final_ranking_score": 72.45,
    "status": "VALID"
  }
]
```

**Verified vs Proposed Field Breakdown**

| Field | Source | Status |
|:--|:--|:--|
| `symbol` | `ranking_engine` | VERIFIED |
| `company_name` | `stock_snapshot_service.identity` | Needs API-layer join |
| `sector` | `ranking_engine` (from `sector_intelligence.classification`) | VERIFIED |
| `industry` | `ranking_engine` (from `sector_intelligence.classification`) | VERIFIED |
| `opportunity_score` | `decision_engine` | VERIFIED |
| `technical_score` | `decision_engine` | VERIFIED |
| `financial_score` | `decision_engine` | VERIFIED |
| `momentum_score` | `decision_engine` | VERIFIED |
| `risk_score` | Not computed by any engine | PROPOSED |
| `recommendation` | `decision_engine` | VERIFIED |
| `current_price` | `stock_snapshot_service.market` | Needs API-layer join |
| `entry_zone_low` / `entry_zone_high` | `signal_engine` (as `entry_lower`/`entry_upper`) | Available via `signal_integration` |
| `stop_loss`, `target`, `risk_reward` | `signal_engine` (as `risk_reward_ratio`) | Available via `signal_integration` |
| `expected_holding_weeks` | No backend source | PROPOSED |
| `rank` | `ranking_engine` | VERIFIED |
| `final_ranking_score` | `ranking_engine` | VERIFIED |
| `status` | `ranking_engine` / `decision_engine` | VERIFIED |

**Frontend Fields Currently Consumed by OpportunityTable.jsx**:
- `symbol`, `opportunity_score`, `current_price`, `technical_score`, `risk_score`, `risk_reward`

**Frontend State Handling**
- **Loading**: Full-page `<LoadingState />` spinner
- **Error**: Full-page `<ErrorState />` with retry
- **Empty Array**: `OpportunityTable` renders empty tbody (no explicit empty-state message)
- **Missing `.toFixed()`**: The component calls `score.toFixed(1)` — will crash if score is `null`

**Backend Team Questions**
1. The ranking engine output includes `opportunity_score`, `sector_score`, `final_ranking_score`, `recommendation`, `sector`, `industry`, `status`, and `rank`. The frontend also needs `current_price`, `company_name`, and signal-derived fields (`entry_zone_low`, `entry_zone_high`, `stop_loss`, `target`, `risk_reward`). Will the API route join this data from `stock_snapshot` and `signal_integration` pipelines?
2. The mock data includes `risk_score` and `expected_holding_weeks`. Do these fields exist in any backend module, or should they be removed from the mock?
3. Should the response return an array directly or be wrapped in an object like `{ "evaluation_date": "...", "opportunities": [...] }`?

---

### 3.3 GET /api/stocks — Stock Universe

| Attribute | Value |
|:--|:--|
| **Verification Status** | **PARTIALLY IMPLEMENTED** — `classification_service.get_all_classifications()` returns all symbols with sector/industry classification. No HTTP route or pagination logic exists. |
| **Frontend Service Function** | `getStocks()` in `frontend/src/services/api.js` |
| **Mock Data File** | `frontend/src/data/mockStocks.js` |
| **Backend Source** | `classification_service.get_all_classifications()` |
| **Consumed By** | `/stocks` route — currently a `PlaceholderPage` |

**Proposed Request**
```
GET /api/stocks?page=1&limit=20&search=TCS&sector=Information+Technology&sort=symbol&order=asc
```

| Parameter | Type | Required | Default | Description |
|:--|:--|:--|:--|:--|
| `page` | integer | No | `1` | Page number (1-indexed) |
| `limit` | integer | No | `20` | Items per page (max 100) |
| `search` | string | No | — | Search by symbol or company name |
| `sector` | string | No | — | Filter by sector name |
| `sort` | string | No | `symbol` | Sort field: `symbol`, `sector`, `company_name` |
| `order` | string | No | `asc` | Sort direction: `asc`, `desc` |

**Proposed Response Schema**
```json
{
  "stocks": [
    {
      "symbol": "TCS",
      "company_name": "Tata Consultancy Services Limited",
      "sector": "Information Technology",
      "industry": "IT Services",
      "current_price": 3520.0,
      "change_percent": 0.72
    }
  ],
  "pagination": {
    "page": 1,
    "limit": 20,
    "total_items": 50,
    "total_pages": 3
  }
}
```

**Field Sources**

| Field | Source | Status |
|:--|:--|:--|
| `symbol` | `classification_service` | VERIFIED |
| `company_name` | `classification_service` | VERIFIED |
| `sector` | `classification_service` | VERIFIED |
| `industry` | `classification_service` | VERIFIED |
| `current_price` | `stock_snapshot_service.market.close` | Needs join |
| `change_percent` | Derived from price data | PROPOSED |
| `pagination` | Server-side logic | PROPOSED |

**Backend Team Questions**
1. Should the stock list include real-time or latest EOD `current_price` and `change_percent`? The classification service only provides identity/classification, not pricing.
2. Is server-side pagination, search, and filtering acceptable for the 50-stock universe, or should the API return all 50 at once?
3. Can `get_all_classifications()` return `company_name`? The current mock only has `symbol`, `company_name`, `sector`.

---

### 3.4 GET /api/stocks/:symbol — Individual Stock Analysis

| Attribute | Value |
|:--|:--|
| **Verification Status** | **IMPLEMENTED (Logic Only)** — `stock_intelligence.get_stock_intelligence()` returns a complete, API-ready payload. No HTTP route exists. |
| **Frontend Service Function** | `getStock(symbol)` in `frontend/src/services/api.js` |
| **Mock Data File** | `frontend/src/data/mockStock.js` |
| **Backend Source** | `stock_intelligence.get_stock_intelligence()` |
| **Consumed By** | `StockDetail.jsx` — currently a placeholder |

**Request**
```
GET /api/stocks/TCS
GET /api/stocks/TCS?evaluation_date=2026-08-14
```

| Parameter | Type | Location | Required | Description |
|:--|:--|:--|:--|:--|
| `symbol` | string | Path | Yes | NSE ticker symbol (e.g., `TCS`, `INFY`) |
| `evaluation_date` | string | Query | No | Historical evaluation date (`YYYY-MM-DD`) |

**Verified Response Schema** (from `stock_intelligence.py` and `docs/week11_unified_intelligence_contract.md` Section 9)

This is the most thoroughly documented schema in the backend. The following JSON matches the verified contract:

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
    "stock_performance": {
      "21D": 0.0727,
      "63D": 0.034,
      "126D": -0.1251,
      "252D": -0.1913
    },
    "sector_performance": {
      "data_quality": "VALID",
      "performance": { "21D": 0.0876, "63D": 0.0585, "126D": -0.075, "252D": -0.0908 },
      "preliminary_score": {
        "score": 64.607,
        "components": { "base": 50.0, "21D_component": 8.7618, "63D_component": 5.8452 }
      }
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
        { "category": "Technical", "metric": "RSI", "value": "52.92", "interpretation": "RSI is in a strong momentum zone (40-70)." }
      ],
      "negative_factors": [
        { "category": "Technical", "metric": "MACD", "value": "MACD: 49.88, Signal: 59.91", "interpretation": "MACD line is below Signal line." }
      ],
      "neutral_factors": [],
      "missing_factors": []
    }
  }
}
```

> **Note**: This schema is directly sourced from the verified `docs/week11_unified_intelligence_contract.md` Section 9 and `stock_intelligence.py`. All fields are sanitized (NaN to null, float to 4dp) and JSON-safe.

**Frontend State Handling**
- `StockDetail.jsx` is currently a placeholder — shows only the symbol name
- Future implementation must handle all nested `null` sections gracefully

**Backend Team Questions**
1. Should the route accept `?evaluation_date=YYYY-MM-DD` for historical analysis?
2. The stock intelligence response is large. Should any sections be lazy-loaded via separate endpoints?

---

### 3.5 GET /api/stocks/:symbol/history — Historical Price Data

| Attribute | Value |
|:--|:--|
| **Verification Status** | **IMPLEMENTED (Logic Only)** — `data_pipeline.historical_data_service.get_historical_data()` returns OHLCV data. No HTTP route exists. |
| **Frontend Service Function** | `getStockHistory(symbol)` in `frontend/src/services/api.js` |
| **Mock Data File** | `frontend/src/data/mockHistory.js` |
| **Backend Source** | `data_pipeline/historical_data_service.get_historical_data()` |
| **Consumed By** | No frontend component currently consumes this (planned for chart feature) |

**Proposed Request**
```
GET /api/stocks/TCS/history?start_date=2025-01-01&end_date=2026-08-28
```

| Parameter | Type | Location | Required | Default | Description |
|:--|:--|:--|:--|:--|:--|
| `symbol` | string | Path | Yes | — | NSE ticker |
| `start_date` | string | Query | No | 1 year ago | Start date (`YYYY-MM-DD`) |
| `end_date` | string | Query | No | Latest | End date (`YYYY-MM-DD`) |

**Verified Response Schema** (based on `historical_data_service` and mock data structure)
```json
[
  {
    "date": "2023-10-01",
    "open": 150.0,
    "high": 155.0,
    "low": 149.0,
    "close": 153.0,
    "volume": 10000
  }
]
```

All fields (date, open, high, low, close, volume) are VERIFIED from the backend `historical_data_service`.

**Backend Team Questions**
1. Should the response include `adjusted_close`? The backend's `historical_data_service` has this field.
2. Should the response support limiting number of data points (e.g., `?limit=252` for 1 year)?
3. The backend has ~500 rows per stock. Is returning all rows acceptable, or should pagination apply?

---

### 3.6 GET /api/sectors — Sector Performance & Analysis

| Attribute | Value |
|:--|:--|
| **Verification Status** | **IMPLEMENTED (Logic Only)** — `sector_industry_engine.run_sector_industry_engine()` and `sector_engine.rank_sectors()` produce ranked sector data with performance, relative strength, and preliminary scores. No HTTP route exists. |
| **Frontend Service Function** | `getSectors()` in `frontend/src/services/api.js` |
| **Mock Data File** | `frontend/src/data/mockSectors.js` |
| **Backend Source** | `sector_industry_engine.run_sector_industry_engine()` then `sector_engine.rank_sectors()` |
| **Consumed By** | `Dashboard.jsx` via `SectorList` component |

**Request**
```
GET /api/sectors?ranking_period=63D
```

| Parameter | Type | Required | Default | Description |
|:--|:--|:--|:--|:--|
| `ranking_period` | string | No | `63D` | Ranking period: `21D`, `63D`, `126D`, `252D` |

**Verified Response Schema** (based on `sector_industry_engine.py` output)
```json
{
  "status": "VALID",
  "evaluation_date": null,
  "ranking_period": "63D",
  "sectors_analyzed": 16,
  "industries_analyzed": 32,
  "sector_rankings": [
    {
      "rank": 1,
      "sector": "Information Technology",
      "performance": 0.085,
      "relative_strength": {
        "benchmark": "NIFTY_50",
        "21D_rs": 0.0151,
        "63D_rs": 0.027,
        "126D_rs": -0.05,
        "252D_rs": -0.1005,
        "status": "VALID"
      },
      "preliminary_score": {
        "score": 64.607,
        "components": { "base": 50.0, "21D_component": 8.76, "63D_component": 5.85 },
        "range": { "min": 0.0, "max": 100.0 }
      },
      "constituents_count": 8,
      "valid_constituents_count": 8,
      "data_quality": "VALID",
      "warnings": []
    }
  ],
  "industry_rankings": []
}
```

All fields in the above schema are VERIFIED from `sector_industry_engine.py` and `sector_engine.py`.

**Frontend Mock vs Backend Mapping**

The current mock (`mockSectors.js`) uses a flat structure. Here is the mapping:

| Mock Field | Backend Field | Notes |
|:--|:--|:--|
| `sector` | `sector_rankings[].sector` | Direct match |
| `performance_21d` | `sector_engine` output `performance["21D"]` | Convert decimal to percentage in frontend |
| `performance_63d` | `sector_engine` output `performance["63D"]` | Convert decimal to percentage |
| `performance_126d` | `sector_engine` output `performance["126D"]` | Convert decimal to percentage |
| `relative_strength_vs_nifty` | `relative_strength["63D_rs"]` | MISMATCH: Mock uses a ratio (1.08), backend uses a difference (0.027) |
| `stock_count` | `constituents_count` | Available |

> **MISMATCH ALERT**: The `SectorList.jsx` component computes a "strength score" as `(relative_strength_vs_nifty * 100) - 20`. This formula assumes a ratio-based value (e.g., 1.08 gives score 88). The backend provides a difference-based value (e.g., 0.027). The frontend formula must be updated during integration.

**Frontend State Handling**
- **Loading**: Full-page `<LoadingState />`
- **Error**: Full-page `<ErrorState />`
- **Empty**: `SectorList` calls `sectors.slice(0, 5)` — shows nothing if empty
- `SectorList` is used on Dashboard, limited to top 5

**Backend Team Questions**
1. Should the frontend simplify the response by requesting a flat sector array, or use the full engine output?
2. The relative strength computation changed from mock (ratio) to backend (difference). Which should the API provide?
3. Should the response include both sector and industry rankings, or should industries be a separate endpoint?

---

### 3.7 GET /api/backtests/latest — Latest Backtest Performance

| Attribute | Value |
|:--|:--|
| **Verification Status** | **IMPLEMENTED (Logic Only)** — `backtest_engine.run_backtest()` and `backtest_metrics.calculate_backtest_metrics()` produce complete performance metrics. No HTTP route exists. The `backtest_results` table has 2 stored records. |
| **Frontend Service Function** | `getLatestBacktest()` in `frontend/src/services/api.js` |
| **Mock Data File** | `frontend/src/data/mockBacktest.js` |
| **Backend Source** | `backtest_engine.run_backtest()` then `backtest_metrics.calculate_backtest_metrics()` |
| **Consumed By** | `/performance` route — currently a `PlaceholderPage` |

**Request**
```
GET /api/backtests/latest
```
No query parameters.

**Response Schema** (verified fields + proposed fields)

```json
{
  "total_trades": 124,
  "closed_trades": 110,
  "open_trades": 8,
  "invalid_trades": 4,
  "incomplete_trades": 2,
  "winning_trades": 69,
  "losing_trades": 41,
  "win_rate": 62.7273,
  "total_pl": 15420.50,
  "total_return_pct": 28.5,
  "avg_trade_return_pct": 2.3,
  "avg_winning_trade_pct": 5.1,
  "avg_losing_trade_pct": -2.4,
  "profit_factor": 1.8,
  "max_drawdown_pct": 12.4,
  "run_id": "backtest_abc123",
  "start_date": "2025-08-01",
  "end_date": "2026-08-01",
  "symbols": ["TCS", "INFY"]
}
```

**Verified vs Proposed Fields**

| Field | Source | Status |
|:--|:--|:--|
| `total_trades` | `backtest_metrics` | VERIFIED |
| `closed_trades` through `losing_trades` | `backtest_metrics` | VERIFIED |
| `win_rate` | `backtest_metrics` | VERIFIED |
| `total_pl`, `total_return_pct` | `backtest_metrics` | VERIFIED |
| `avg_trade_return_pct` | `backtest_metrics` | VERIFIED |
| `avg_winning_trade_pct`, `avg_losing_trade_pct` | `backtest_metrics` | VERIFIED |
| `profit_factor` | `backtest_metrics` | VERIFIED |
| `max_drawdown_pct` | `backtest_metrics` | VERIFIED |
| `run_id`, `start_date`, `end_date`, `symbols` | `backtest_engine` | VERIFIED |
| `strategy_name` (in mock) | None | PROPOSED — Not in backend |
| `period` (in mock) | Derivable from start/end | PROPOSED |
| `sharpe_ratio` (in mock) | None | PROPOSED — Not computed |
| `cagr` (in mock) | None | PROPOSED — Not computed |
| `last_updated` (in mock) | None | PROPOSED — Needs timestamp |

**Backend Team Questions**
1. Should `sharpe_ratio` and `cagr` be added to `backtest_metrics.py`, or should the frontend drop these fields?
2. Should the API return the full trade list, or just the summary metrics?
3. How should `latest` be determined — most recent `run_id`, or a dedicated "latest backtest" persistence layer?

---

### 3.8 GET /api/data-health — Data Pipeline Health

| Attribute | Value |
|:--|:--|
| **Verification Status** | **PARTIALLY IMPLEMENTED** — `data_pipeline/week15_quality_monitor.py` and `data_pipeline/consolidated_quality_report.py` produce detailed health data. No HTTP route or simplified health endpoint exists. |
| **Frontend Service Function** | `getDataHealth()` in `frontend/src/services/api.js` |
| **Mock Data File** | `frontend/src/data/mockMarket.js` (exported as `mockDataHealth`) |
| **Consumed By** | `Dashboard.jsx` — Data Health section |

**Request**
```
GET /api/data-health
```
No query parameters.

**Proposed Response Schema** (informed by backend quality monitor)
```json
{
  "market_data": "Healthy",
  "technical_data": "Healthy",
  "financial_data": "Healthy",
  "last_updated": "2026-10-11T15:24:10.000Z",
  "universe_count": 50,
  "market_rows": 25495,
  "technical_rows": 25495,
  "financial_records": 280,
  "date_range": {
    "start": "2024-08-14",
    "end": "2026-08-28"
  }
}
```

**Frontend Fields Currently Consumed**:
- `health.market_data`, `health.technical_data`, `health.financial_data`, `health.last_updated`
- Extended fields (`universe_count`, etc.) are proposed additions

**Frontend State Handling**
- If `health` is null/undefined, shows "Health status unavailable."
- Renders status badges with green styling (currently hardcoded for "Healthy")
- Displays `last_updated` via `new Date(health.last_updated).toLocaleString()`

**Backend Team Questions**
1. Should the health endpoint run a live quality check, or return cached results from the last pipeline run?
2. The frontend uses `new Date()` to parse `last_updated`. Is ISO 8601 guaranteed?
3. Should the status values map to the existing quality report statuses or use simplified labels?

---

## 4. Error Handling Conventions

### 4.1 HTTP Status Codes

The frontend `request()` wrapper in `api.js` handles errors as follows:

| Scenario | Frontend Behaviour |
|:--|:--|
| Network failure (DNS, timeout, refused) | Throws `Error("Network Error: Failed to reach the API. ...")` |
| HTTP 4xx/5xx response | Throws `Error("API error: {status} {statusText}")` with `.status` property |
| Missing `VITE_API_BASE_URL` (real mode) | Throws `Error("Configuration Error: ...")` |

### 4.2 Proposed Backend Error Response Format

```json
{
  "error": {
    "code": "NOT_FOUND",
    "message": "Stock symbol XYZ not found",
    "status": 404
  }
}
```

| HTTP Status | When |
|:--|:--|
| `200` | Success |
| `400` | Invalid parameters (bad symbol, invalid date format) |
| `404` | Resource not found (unknown symbol) |
| `500` | Internal server error (engine failure) |
| `503` | Database or pipeline unavailable |

### 4.3 Critical Rule: No Silent Fallback

> Mock data MUST NOT silently replace failed API requests. The `api.js` architecture enforces this: mock data is loaded **only** when `VITE_USE_MOCK_DATA === "true"`, never as a fallback for failed requests.

---

## 5. Data Representation Conventions

### 5.1 Dates & Timestamps

| Type | Format | Example |
|:--|:--|:--|
| Calendar dates | `YYYY-MM-DD` (ISO 8601 date) | `"2026-08-14"` |
| Timestamps | ISO 8601 with timezone | `"2026-10-11T15:24:10.000Z"` |
| Evaluation date parameter | `YYYY-MM-DD` string | `?evaluation_date=2026-08-14` |

### 5.2 Missing & Unavailable Data

| Backend Representation | Frontend Handling |
|:--|:--|
| `null` | Display "N/A" or hide the element |
| `"INSUFFICIENT"` / `"INSUFFICIENT_DATA"` status | Show explanatory message, not error state |
| Score of `null` | Do NOT call `.toFixed()` — guard with null check |
| Empty array `[]` | Show empty-state component |
| `NaN` / `Infinity` | Backend sanitizes to `null` (verified in `stock_intelligence._sanitize_primitives()`) |

### 5.3 Numeric Precision

- Scores: Backend rounds to 4 decimal places
- Prices: 2 decimal places for display (frontend formats)
- Percentages: Backend returns performance as decimals (e.g., `0.072` for 7.2%); frontend multiplies by 100 where needed

### 5.4 Pagination Conventions

For the 50-stock universe:
- Default page size: 20
- Maximum page size: 100
- Page numbering: 1-indexed
- Response includes `pagination` object with `page`, `limit`, `total_items`, `total_pages`

### 5.5 Historical Evaluation Dates

- All engines support point-in-time evaluation via `evaluation_date` parameter
- Data lookup is restricted to records at or before `evaluation_date`
- If `evaluation_date` is omitted, latest available data is used
- This prevents lookahead/future data leakage in historical analysis

### 5.6 Market Data Freshness

- `last_updated` timestamps should be provided by the backend from actual pipeline run times
- Frontend displays via `new Date(timestamp).toLocaleString()` — ISO 8601 format required
- Data freshness should NOT be computed on the frontend using `new Date()` (as the mock currently does)

---

## 6. Mock-to-Real Integration Workflow

### 6.1 Environment Configuration

```bash
# frontend/.env.local (for real API mode)
VITE_API_BASE_URL=http://localhost:5000
VITE_USE_MOCK_DATA=false

# frontend/.env.local (for mock development mode)
VITE_USE_MOCK_DATA=true
# VITE_API_BASE_URL not required when using mock
```

### 6.2 How the Switch Works

Each service function (e.g., `getOpportunities()`) checks `USE_MOCK` at the top:
1. If `true`: dynamically imports mock data file and returns mock data
2. If `false`: calls `request(path)` which calls `fetch(BASE_URL + path)` and returns parsed JSON

The decision is made once at module load time based on `VITE_USE_MOCK_DATA`. There is no per-request fallback.

### 6.3 Integration Steps Per Endpoint

1. Backend team implements and deploys the HTTP route
2. Backend team confirms response schema matches this contract
3. Frontend developer updates `VITE_API_BASE_URL` to point to the running backend
4. Frontend developer sets `VITE_USE_MOCK_DATA=false`
5. Frontend developer verifies the component renders correctly with real data
6. If response fields differ from mock structure, update the component data mapping
7. Add null guards for any fields that can be `null` in real data but were always present in mock

### 6.4 What Must NOT Happen

- Do not silently replace failed API requests with mock data
- Do not change `VITE_USE_MOCK_DATA` to `true` in production
- Do not hard-code API URLs in component files
- Do not call `fetch()` directly from components — always use `api.js` service functions

---

## 7. Frontend / Backend Responsibility Boundaries

### 7.1 Backend is Responsible For

| Responsibility | Backend Module |
|:--|:--|
| Opportunity Score calculation (40/35/25 weighting) | `decision_engine.py` |
| Final Ranking Score (70/30 opportunity + sector) | `ranking_engine.py` |
| Technical indicator computation (RSI, MACD, EMA, ATR) | `technical_engine.py` |
| Financial health scoring (ROE, ROCE, D/E, margins) | `financial_engine.py` |
| Recommendation logic (BUY >= 75, WATCH >= 60, HOLD >= 45, AVOID < 45) | `decision_engine.py` |
| Signal generation (entry zone, stop loss, target) | `signal_engine.py` |
| Trade quality and risk flags | `trade_quality_engine.py` |
| Structured explanations | `explanation/` |
| Backtesting and metrics | `backtest_engine.py` |
| Sector ranking and relative strength | `sector_engine.py` |
| Point-in-time historical evaluation | All engines |
| Data freshness / pipeline health | `week15_quality_monitor.py` |
| JSON sanitization (NaN to null) | `stock_intelligence._sanitize_primitives()` |

### 7.2 Frontend is Responsible For

| Responsibility | Details |
|:--|:--|
| Number formatting | Currency (INR), percentages, multipliers (e.g., 2.1x) |
| Color mapping | Recommendation to color (BUY = green, AVOID = red) |
| Score bar widths | `(score / 100) * 100%` |
| Relative strength label | Maps backend score to "Strong" / "Neutral" / "Weak" |
| Theme (dark/light mode) | `useTheme` hook |
| Pagination UI | Page navigation controls |
| Search/filter UI | Input debouncing, filter chips |
| Chart rendering | OHLCV data to candlestick/line charts |
| Error display | Maps API errors to user-friendly messages |
| Timestamp display | `new Date(iso).toLocaleString()` |

### 7.3 What the Frontend MUST NOT Do

- Calculate opportunity scores, financial scores, or technical scores
- Derive recommendations from scores
- Compute entry zones, stop losses, or targets
- Run backtests or compute performance metrics
- Calculate relative strength or sector rankings
- Silently fall back to mock data on API failure

---

## 8. Backend Team Questions

### Critical (Blocking Integration)

1. **API Framework**: Which framework will be used for the REST API layer? Flask, FastAPI, or another? (`backend/app.py` is currently empty.)
2. **API Port**: Is `http://localhost:5000` confirmed as the development API server port? (Currently a placeholder in `.env.example`.)
3. **CORS**: Will the backend configure CORS headers for `http://localhost:5173` (Vite dev server)?
4. **Response Wrapping**: Will responses be wrapped in a standard envelope (e.g., `{ "data": ..., "meta": ... }`) or returned as bare JSON?

### Data Availability

5. **Market Indices**: Does the backend plan to provide NIFTY 50 / SENSEX index data? The current database stores only individual stock prices for a 50-stock universe.
6. **Current Price**: How will `current_price` be included in opportunities and stock-list responses? Via the `stock_snapshot_service.market.close` field?
7. **Refresh Frequency**: What is the data staleness threshold? The database covers up to 2026-08-28. Will there be a daily update pipeline?

### Schema Confirmations

8. **Risk Score**: The mock data includes `risk_score`. Is this planned? No backend module currently computes it.
9. **Expected Holding Weeks**: Same question — `expected_holding_weeks` appears in mocks but not in the backend.
10. **Sharpe Ratio and CAGR**: Are these planned additions to `backtest_metrics.py`?
11. **Sector Relative Strength Format**: The mock uses a ratio (1.08), the backend uses a difference (0.027). Which should the API return?

### Architecture

12. **Pagination**: For the 50-stock universe, is server-side pagination needed, or should the API return all stocks?
13. **Historical Date Support**: Should API endpoints support `?evaluation_date=YYYY-MM-DD` for point-in-time analysis?
14. **Authentication**: Is auth planned for any phase? The `api.js` has a placeholder for `Authorization: Bearer ${token}`.

---

## 9. Integration Readiness Checklist

### Frontend Readiness

| Item | Status | Details |
|:--|:--|:--|
| API service layer (`api.js`) | Ready | 8 service functions defined matching 8 endpoints |
| Mock data for offline dev | Ready | 7 mock data files covering all endpoints |
| Mock/real mode switching | Ready | `VITE_USE_MOCK_DATA` environment variable |
| Error handling (`request()` wrapper) | Ready | Network errors, HTTP errors, config errors |
| Loading state component | Ready | `<LoadingState />` |
| Error state component | Ready | `<ErrorState />` with retry |
| Empty state component | Ready | `<EmptyState />` |
| Dashboard page | Ready | Consumes `getMarketIndices`, `getOpportunities`, `getSectors`, `getDataHealth` |
| Stock detail page | Placeholder | Route exists, `getStock()` ready, UI not built |
| Stocks list page | Placeholder | Route exists, `getStocks()` ready, UI not built |
| Sectors page | Placeholder | Route exists, `getSectors()` ready, UI not built |
| Performance page | Placeholder | Route exists, `getLatestBacktest()` ready, UI not built |

### Backend Readiness

| Item | Status | Details |
|:--|:--|:--|
| REST API framework setup | Not Started | `app.py` is empty, `api/` has only `.gitkeep` |
| Route: `/api/market/indices` | Not Started | No index data source exists |
| Route: `/api/opportunities` | Not Started | Logic exists (`rank_universe`), needs HTTP wrapper |
| Route: `/api/stocks` | Not Started | Logic exists (`get_all_classifications`), needs route + pagination |
| Route: `/api/stocks/:symbol` | Not Started | Logic exists (`get_stock_intelligence`), needs route |
| Route: `/api/stocks/:symbol/history` | Not Started | Logic exists (`get_historical_data`), needs route |
| Route: `/api/sectors` | Not Started | Logic exists (`run_sector_industry_engine`), needs route |
| Route: `/api/backtests/latest` | Not Started | Logic exists (`run_backtest`), needs route + "latest" resolver |
| Route: `/api/data-health` | Not Started | Logic exists (`week15_quality_monitor`), needs route |
| CORS configuration | Not Started | Required for frontend dev server |
| Error response format | Not Started | Standard error envelope needed |
| Response serialization | Partial | `_sanitize_primitives()` handles NaN/Inf, but no JSON serialization layer |

### Phase Dependencies

| Frontend Phase | Required APIs | Backend Status |
|:--|:--|:--|
| Dashboard (current) | `market/indices`, `opportunities`, `sectors`, `data-health` | All need HTTP routes |
| Stock Detail Page | `stocks/:symbol`, `stocks/:symbol/history` | Needs HTTP routes |
| Stocks List Page | `stocks` (with search/filter/pagination) | Needs HTTP route |
| Sectors Page | `sectors` (full view) | Needs HTTP route |
| Performance Page | `backtests/latest` | Needs HTTP route |
| Real-time Integration | All endpoints | All need HTTP routes + CORS |

---

## Appendix A: File Reference Map

### Frontend Files

| File | Purpose |
|:--|:--|
| `frontend/src/services/api.js` | Central API service layer (8 functions) |
| `frontend/src/data/mockOpportunities.js` | Mock swing opportunities (2 records) |
| `frontend/src/data/mockStocks.js` | Mock stock universe (5 records) |
| `frontend/src/data/mockStock.js` | Mock single stock intelligence |
| `frontend/src/data/mockSectors.js` | Mock sector data (3 records) |
| `frontend/src/data/mockMarket.js` | Mock market indices + data health |
| `frontend/src/data/mockHistory.js` | Mock OHLCV history (5 records) |
| `frontend/src/data/mockBacktest.js` | Mock backtest metrics |
| `frontend/.env.example` | Environment variable template |

### Backend Files (Read-Only Reference)

| File | Purpose |
|:--|:--|
| `backend/app.py` | Empty — API framework not yet set up |
| `backend/engines/universe_orchestrator.py` | End-to-end universe ranking |
| `backend/engines/decision_engine.py` | Composite Opportunity Score |
| `backend/engines/ranking_engine.py` | Top 10 ranking |
| `backend/engines/sector_industry_engine.py` | Sector and industry rankings |
| `backend/logic/stock_intelligence.py` | Full stock intelligence payload |
| `backend/logic/backtest_engine.py` | Historical backtesting |
| `backend/logic/backtest_metrics.py` | Performance metrics calculator |
| `backend/logic/signal_engine.py` | Entry zone, stop loss, targets |
| `backend/logic/sector_engine.py` | Sector evaluation and ranking logic |

### Documentation Reference

| File | Purpose |
|:--|:--|
| `docs/week11_unified_intelligence_contract.md` | Verified stock intelligence schema (Section 9 JSON example) |
| `docs/week16_handoff.md` | Logic engine final sign-off (330/330 tests) |
| `docs/week15_data_health_report.md` | Database health audit (50 companies, 25K rows) |
| `docs/frontend-phase-01-audit.md` | Phase 1 frontend audit |
