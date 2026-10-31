# AUDIT-015: Historical Data Eligibility and Point-in-Time Integrity Review

**Project:** Swing Trading Intelligence Platform — Indian Equities  
**Scope:** Architectural trace of all historical market data, technical indicator, and fundamental financial lookup call paths  
**Verification Date:** 2026-10-29  
**Audit Finding:** **STRICT POINT-IN-TIME MARKET DATA; ASYMMETRIC FINANCIAL DATA ELIGIBILITY**

---

## 1. Executive Summary & Code Trace

An exhaustive trace of all historical data lookup call paths was conducted across the data pipeline, analytics logic, and decision engines:

| Lookup Domain | Call Path / Function | Historical Date Parameter | Lookahead Behavior & Safety Status |
| :--- | :--- | :---: | :--- |
| **Market Data (OHLCV)** | `get_stock_data(symbol, end_date=evaluation_date)` | `end_date` | **Strictly Point-in-Time.** Filters `WHERE date <= ?`. Zero future candles leak into earlier evaluations. |
| **Technical Indicators & ATR** | `get_stop_target_inputs(symbol, evaluation_date=dt)` | `evaluation_date` | **Strictly Point-in-Time.** Indicators and support/resistance zones are computed strictly on data $\le dt$. |
| **Volatility & ATR Metrics** | `analyze_volatility(symbol, evaluation_date=dt)` | `evaluation_date` | **Strictly Point-in-Time.** Uses price history up to `evaluation_date`. |
| **Valuation Metrics (P/E, EPS)**| `analyze_valuation(symbol, evaluation_date=dt)` | `evaluation_date` | **Point-in-Time Gated.** Calls `get_latest_financial_data` with SEBI 45-day fallback. |
| **Snapshot Fundamental Handoff**| `get_stock_snapshot(symbol, evaluation_date=dt)` | `evaluation_date` | **Point-in-Time Gated.** Enforces publication date / 45-day lag. |
| **Core Financial Health Analyzers**| `analyze_roe`, `analyze_roce`, `analyze_debt_equity`, `analyze_profit_margin`, `analyze_growth` | **None (Missing)** | **Static Snapshot Limitation.** Calls `get_financial_data(symbol)` which queries all quarters in DB without date filtering. |

---

## 2. Asymmetric Fundamental Gating Analysis

### The Dual Fundamental Architecture:
1. **Gated Paths (`get_latest_financial_data`):**
   - Implemented in `backend/data_pipeline/financial_service.py:182-320`.
   - If `publication_date` is present: requires `pub_ts <= eval_ts` (Status: `VERIFIED_POINT_IN_TIME`).
   - If `publication_date` is `NULL` (100% of current active DB rows): requires `period_end + 45 days <= eval_ts` (Status: `PERIOD_ELIGIBLE_FALLBACK_LAG`).
   - Gated calls in `stock_snapshot_service.py` and `valuation_analyzer.py` properly hide future quarters from earlier dates.
2. **Ungated Legacy Paths (The 5 Sub-Analyzers):**
   - In `backend/engines/financial_engine.py:255-262`, `analyze_financial_health` receives `evaluation_date`, but only passes it to `analyze_volatility` and `analyze_valuation`.
   - It invokes `analyze_roe(norm_symbol)`, `analyze_roce(norm_symbol)`, `analyze_debt_equity(norm_symbol)`, `analyze_profit_margin(norm_symbol)`, and `analyze_growth(norm_symbol)`.
   - These 5 functions call `get_financial_data(symbol)`, which runs `SELECT ... FROM quarterly_results WHERE symbol = ? ORDER BY quarter ASC` with no date filter.
   - They evaluate `valid_series.iloc[-1]`, reading the newest quarter in the database (`2026-Q1`) even when evaluating a date in `2025-10-01`.

### Critical Finding:
> [!IMPORTANT]
> **We do NOT claim zero lookahead bias across the entire platform.**  
> While market prices and valuation multiples are strictly lookahead-free, the fundamental profitability sub-scores (ROE, ROCE, Profit Margin, Debt-to-Equity, Revenue Growth) evaluate the full 5-quarter dataset regardless of historical evaluation date.

---

## 3. Publication Dates vs Estimated Fallback Dates

- **Actual Publication Dates:** Require verified corporate disclosure timestamps lodged with the National Stock Exchange (NSE) or Bombay Stock Exchange (BSE).
- **Current Database Reality:** Exactly **0 of the 260 quarterly records** in `database/swing_trading.db` possess a non-null `publication_date`.
- **Visibility:** When `get_latest_financial_data` executes, records without publication dates are explicitly tagged:
  - `status: "PERIOD_ELIGIBLE_FALLBACK_LAG"`
  - `is_verified: False`
- **Methodological Distinction:** The 45-day fallback provides **conservative lookahead immunity** (ensuring results are not used before the statutory deadline), but does **not** reflect real-world announcement dates.

---

## 4. Timezone & String Formatting Invariants

- **Internal Date Format:** All internal database records use `YYYY-MM-DD` strings.
- **Timestamp Construction:** `financial_service.py` converts date strings into end-of-day tz-naive Timestamps (`YYYY-MM-DD 23:59:59.999999`).
- **Latent Risk:** If an external caller passes a timezone-aware ISO 8601 string (e.g. `2025-10-01T09:15:00+05:30`), pandas will raise `TypeError: Cannot compare tz-naive and tz-aware timestamps`. To avoid this, date inputs must remain tz-naive string format.

---

## 5. Strategy Dependence on Publication Timing

- The platform's trading strategy is **swing trading based on market structure, pullback entry zones, and support/resistance boundaries**.
- The strategy does **not** trade earnings momentum, earnings surprises, or Post-Earnings Announcement Drift (PEAD).
- Fundamentals act purely as a high-level qualification screen (Opportunity Score $\ge 70.0$).
- Therefore, the 45-day fallback is structurally acceptable for technical swing trading, but unsuited for earnings-driven fundamental event strategies.

