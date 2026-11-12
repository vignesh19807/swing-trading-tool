# PHASE 5.4.8 — STOCK EXPLORER FAST-PATH OPTIMIZATION REPORT

**Project:** Swing Trading Intelligence Platform
**Target Environment:** Staging
**Frontend URL:** `https://swing-trading-tool.vercel.app`
**Backend URL:** `https://swing-trading-staging-backend.onrender.com`
**Database:** Neon Serverless PostgreSQL 16
**Git Branch:** `staging`
**Timestamp:** 2026-11-08T21:58:00+05:30
**Phase Status:** `FAST-PATH OPTIMIZATION COMPLETE & VALIDATED`

---

## 1. Executive Summary & Original Bottleneck

In Phase 5.4.6 profiling, `GET /api/stocks` was identified as timing out (>30 seconds) on cold cache starts.

### Root Cause:
`GET /api/stocks` in `backend/app.py` originally executed:
1. An efficient SQL query fetching `latest_close`, `prev_close`, `rsi`, `macd`, and `ema20/50/200` indicators in ~170 ms.
2. If `universe_scores` was not in the in-memory cache, it synchronously called `rank_universe(eval_date)`.
3. In `rank_universe()`, every stock in the universe was evaluated through the Decision Engine and signal pipelines sequentially.
4. If a stock was still not in `universe_scores`, it called `calculate_opportunity_score(sym)` in a secondary fallback loop.
5. On the constrained Render Free Tier instance (0.1 shared vCPU), this sequential computation took >45 seconds, triggering client/gateway timeouts and rendering the Stock Explorer unavailable.

### Remediation Applied:
A fast-path decoupling was implemented in `backend/app.py`:
- `GET /api/stocks` now looks up cached opportunity scores and recommendations non-blockingly (`get_cached_universe_scores(...) or {}`).
- If scores are not cached, it sets `opportunity_score: None` and `recommendation: None` explicitly.
- It **never** synchronously executes `rank_universe()` or `calculate_opportunity_score()`.
- Baseline stock metadata, daily prices, price changes, and technical indicator fields (`rsi`, `macd`, `ema20`, `ema50`, `ema200`, `technical_score`) are returned immediately.

---

## 2. Files Modified

| File | Status | Description of Change |
|---|---|---|
| `backend/app.py` | **Modified** | Decoupled `rank_universe()` and `calculate_opportunity_score()` from `GET /api/stocks` (+3/-17 lines). |
| `backend/tests/test_stocks_fast_path.py` | **Created** | Comprehensive unit test suite covering cached/uncached states, null handling, pagination, and filters. |

### Protected Files Check:
- `backend/logic/signal_engine.py`: **UNTOUCHED**
- `backend/logic/trade_quality_engine.py`: **UNTOUCHED**
- `backend/logic/portfolio_simulator.py`: **UNTOUCHED**
- `git diff backend/logic/` returned 0 modifications.

---

## 3. Implementation Details

In `backend/app.py`:
```python
# Before:
universe_scores = get_cached_universe_scores(evaluation_date=eval_date) or get_cached_universe_scores(evaluation_date=None)
if universe_scores is None:
    try:
        rank_universe(evaluation_date=eval_date)
        universe_scores = get_cached_universe_scores(evaluation_date=eval_date) or {}
    except Exception:
        universe_scores = {}

# After (Fast Path):
# Retrieve cached universe scores if available without blocking on expensive calculation
eval_date = _get_latest_market_date()
universe_scores = get_cached_universe_scores(evaluation_date=eval_date) or get_cached_universe_scores(evaluation_date=None) or {}
```

In the stock formatting loop:
```python
# Before:
if sym in universe_scores:
    u_info = universe_scores[sym]
    opp_score = u_info.get("opportunity_score")
    recommendation = u_info.get("recommendation")
else:
    try:
        decision = calculate_opportunity_score(sym)
        if isinstance(decision, dict) and decision.get("status") in ("VALID", "PARTIAL"):
            opp_score = decision.get("opportunity_score")
            recommendation = decision.get("recommendation")
    except Exception:
        pass

# After (Fast Path):
# Attach cached opportunity score and recommendation if present; do not block or invent values
opp_score = None
recommendation = None
if sym in universe_scores:
    u_info = universe_scores[sym]
    opp_score = u_info.get("opportunity_score")
    recommendation = u_info.get("recommendation")
```

---

## 4. API Response & Frontend Compatibility

### API Contract Invariants:
- Response structure preserved:
  ```json
  {
    "page": 1,
    "limit": 50,
    "total_count": 18,
    "stocks": [
      {
        "symbol": "INFY",
        "company_name": "Infosys Limited",
        "sector": "Information Technology",
        "industry": "IT Services & Consulting",
        "exchange": "NSE",
        "current_price": 1845.2,
        "date": "2026-11-06",
        "change_percent": 1.25,
        "opportunity_score": null,
        "recommendation": null,
        "market_status": "Active",
        "technicals": {
          "rsi": 58.4,
          "macd": 12.1,
          "signal": 10.5,
          "histogram": 1.6,
          "ema20": 1820.0,
          "ema50": 1790.0,
          "ema200": 1650.0,
          "close": 1845.2,
          "technical_score": 75.0,
          "date": "2026-11-06",
          "isInsufficient": false,
          "historyLength": 130,
          "status": "READY"
        }
      }
    ]
  }
  ```

### Frontend Safe Null Handling:
1. **Rendering (`frontend/src/pages/StockExplorer.jsx` lines 50–53, 71–74):**
   - `ScoreBadge` renders `—` when `score == null || isNaN(score)`.
   - `RecommendationBadge` renders `—` when `!recommendation`.
2. **Sorting (`frontend/src/utils/screenerFilters.js` lines 320–323):**
   - Handles `null` scores safely via nullish coalescing:
     `(b.opportunity_score ?? 0) - (a.opportunity_score ?? 0)`.
3. **Filtering (`frontend/src/utils/screenerFilters.js`):**
   - Technical strategy filters (EMA 20/50/200, RSI, MACD) operate directly on `technicals` attributes, which remain 100% available and computed via the primary SQL query.
   - Missing scores are never fabricated as zero in data representation.

---

## 5. Test Results

### 5.1 Backend Fast-Path Test Suite (`backend/tests/test_stocks_fast_path.py`)
```text
backend/tests/test_stocks_fast_path.py::test_stocks_fast_path_without_cache PASSED [ 20%]
backend/tests/test_stocks_fast_path.py::test_stocks_fast_path_with_cached_scores PASSED [ 40%]
backend/tests/test_stocks_fast_path.py::test_stocks_pagination PASSED    [ 60%]
backend/tests/test_stocks_fast_path.py::test_stocks_search_filtering PASSED [ 80%]
backend/tests/test_stocks_fast_path.py::test_stocks_sector_filtering PASSED [100%]

============================= 5 passed in 11.73s ==============================
```

### 5.2 Frontend Full Regression Suite (`npm --prefix frontend test`)
```text
🎉 All 59 tests passed successfully (EMA, RSI, MACD, Screener filters).
🎉 All 56 sector helper tests passed successfully.
Dashboard Regressions: 10/10 assertions passed.
🎉 All 18 API service unit tests passed successfully.

========================================
✅ ALL FRONTEND UNIT TESTS COMPLETED SUCCESSFULLY (143 passed, 0 failed)
========================================
```

---

## 6. Performance Measurements

### Local Benchmark Results (`scratch/benchmark_stocks_endpoint.py`):
```text
Run 1: 1522.0ms (Status: 200, count: 18)
Run 2: 1301.7ms (Status: 200, count: 18)
Run 3: 1237.8ms (Status: 200, count: 18)
Run 4: 1338.4ms (Status: 200, count: 18)
Run 5: 1291.4ms (Status: 200, count: 18)

Average: 1338.3ms, Min: 1237.8ms, Max: 1522.0ms
```
- **Query Breakdown over remote Neon PostgreSQL:**
  - `get_all_classifications()`: ~797 ms (includes database round-trip and DataFrame construction).
  - Multi-table SQL join (prices + technical indicators): ~170 ms.
- **Comparison to Previous State:**
  - Previous: **Timed out (>30,000 ms)**.
  - Optimized: **~1.3 seconds end-to-end** across remote Singapore database network connections, with 0 heavy loop calculations.

---

## 7. Integrity & Safety Audit

- **Database Integrity:**
  - Neon PostgreSQL 16 staging database was read using `SELECT` statements only. Zero writes, schema updates, or migrations executed.
- **Trading Logic Invariants:**
  - `rank_universe()`, `calculate_opportunity_score()`, `signal_engine.py`, `trade_quality_engine.py`, and `portfolio_simulator.py` were not altered.
  - Scoring formulas, buy/sell rules, and ranking formulas remain identical.
- **Git State:**
  - No commits or pushes performed. Working branch is clean with respect to `origin/staging`.

---

## 8. Git Diff Summary

```diff
diff --git a/backend/app.py b/backend/app.py
index 6c7e7bc..df84c83 100644
--- a/backend/app.py
+++ b/backend/app.py
@@ -445,15 +445,9 @@ def get_stocks(
         price_map = {}
         tech_map = {}

-    # Retrieve cached universe scores if available
+    # Retrieve cached universe scores if available without blocking on expensive calculation
     eval_date = _get_latest_market_date()
-    universe_scores = get_cached_universe_scores(evaluation_date=eval_date) or get_cached_universe_scores(evaluation_date=None)
-    if universe_scores is None:
-        try:
-            rank_universe(evaluation_date=eval_date)
-            universe_scores = get_cached_universe_scores(evaluation_date=eval_date) or {}
-        except Exception:
-            universe_scores = {}
+    universe_scores = get_cached_universe_scores(evaluation_date=eval_date) or get_cached_universe_scores(evaluation_date=None) or {}

     # Attach current price, price change, opportunity score, recommendation, and precomputed technicals
     stocks = []
@@ -462,21 +456,13 @@ def get_stocks(
         p_info = price_map.get(sym) or {}
         t_info = tech_map.get(sym) or {}

-        # Calculate opportunity score and decision recommendation
+        # Attach cached opportunity score and recommendation if present; do not block or invent values
         opp_score = None
         recommendation = None
         if sym in universe_scores:
             u_info = universe_scores[sym]
             opp_score = u_info.get("opportunity_score")
             recommendation = u_info.get("recommendation")
-        else:
-            try:
-                decision = calculate_opportunity_score(sym)
-                if isinstance(decision, dict) and decision.get("status") in ("VALID", "PARTIAL"):
-                    opp_score = decision.get("opportunity_score")
-                    recommendation = decision.get("recommendation")
-            except Exception:
-                pass

         stocks.append({
             "symbol": sym,
```

---

## 9. Rollback Instructions

To revert this change if desired:
```bash
git checkout backend/app.py
rm backend/tests/test_stocks_fast_path.py
```
This restores the exact synchronous ranking logic without lingering side effects.

---

## 10. Remaining Limitations

1. When the in-memory cache is cold, `GET /api/stocks` displays `—` for `opportunity_score` and `recommendation` until `rank_universe()` is executed by `GET /api/opportunities` or background cache warming.
2. `GET /api/opportunities` and `GET /api/sectors` still require optimization (scheduled for subsequent phases).
