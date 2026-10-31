# Browser & End-to-End User Journey Test Results

## Test Environment
* **Frontend Dev Server:** `http://127.0.0.1:5173`
* **Backend REST API:** `http://127.0.0.1:8000`
* **Database:** SQLite (`database/swing_trading.db`, 52 supported Indian equities)

---

### Journey A: Open Application & Dashboard Initial Load
1. **Entry URL:** `http://127.0.0.1:5173/`
2. **Readiness Probe:** `GET /healthz/ready` returned HTTP 200 with `companies_count: 52`.
3. **Data Health Probe:** `GET /api/data-health` returned HTTP 200 with pipeline factors healthy.
4. **Market Overview:** `GET /api/market/indices` returned benchmark indices.
5. **Top Opportunities:** `GET /api/opportunities` rendered opportunity table.
6. **Result:** **PASS** (Zero console errors, zero failed network calls).

---

### Journey B: Explore Stocks (Stock Explorer)
1. **Route:** `/stocks`
2. **Universe Retrieval:** `GET /api/stocks` populated table with 52 companies.
3. **Filtering & Sorting:** Filtered by sector (e.g., Information Technology), price bands, and opportunity score. Verified client-side filtering via `screenerFilters.test.js`.
4. **Symbol Selection:** Clicking symbol (e.g., `TCS`) navigates smoothly to `/stocks/TCS`.
5. **Result:** **PASS**

---

### Journey C: Inspect Stock Details (Stock Detail Page)
1. **Route:** `/stocks/TCS`
2. **Payload Retrieval:** `GET /api/stocks/TCS` returned unified snapshot including technical, financial, momentum, sector context, and trading setup.
3. **History Candle Fetch:** `GET /api/stocks/TCS/history?timeframe=1M` returned 496 historical OHLCV records.
4. **Technical & Financial Cards:** Rendered RSI, MACD, Moving Averages, ROE, ROCE, Debt/Equity with transparent missing-data handling.
5. **Result:** **PASS**

---

### Journey D: Inspect Opportunities & Rankings
1. **Route:** `/opportunities`
2. **Ranking Verification:** `GET /api/opportunities` returned sorted candidates.
3. **Explanation Consistency:** Explanations explicitly align with recommendation status (e.g. ineligible signals display risk flags instead of falsified buy setups).
4. **Result:** **PASS**

---

### Journey E: Performance & Backtesting Dashboard
1. **Route:** `/performance`
2. **Backtest Retrieval:** `GET /api/backtests/latest` returned persisted run details, metrics, and equity curve.
3. **Equity Curve Visualization:** Rendered drawdown series and cash progression cleanly without division-by-zero crashes.
4. **Result:** **PASS**

---

### Journey F: Negative & Failure Testing
1. **Non-existent Symbol:** `GET /api/stocks/INVALID_SYM_XYZ` returns structured `INSUFFICIENT` data payload with warnings.
2. **Invalid Parameter Format:** Path traversal (`../../etc`) is sanitized and handled gracefully without disclosing internal file structure.
3. **Result:** **PASS WITH LIMITATIONS** (Documented in DEF-001).

