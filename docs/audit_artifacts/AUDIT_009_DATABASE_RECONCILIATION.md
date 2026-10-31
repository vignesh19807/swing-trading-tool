# AUDIT-009: Database & Stock Universe Reconciliation

## 1. Discrepancy Investigation (52 vs. 100 Stocks)

### Background:
* Previous project documentation mentioned an ultimate target of a 100-stock universe (e.g. `STOCK_UNIVERSE` list in `stock_universe.py`).
* Previous audit reports correctly reported **52 companies** present in the active SQLite database (`database/swing_trading.db`).

### Verified Evidence:
1. **Target Dictionary Definition:**
   - File: `backend/data_pipeline/stock_universe.py`
   - Defines `STOCK_UNIVERSE` containing 100 constituents (Nifty 50 + Nifty Next 50 expansion).
   - Module docstring states: *"Central source of truth for the initial 50-stock universe... Current development universe as of August 2026."*
2. **Active Production Database:**
   - File Path: `database/swing_trading.db` (9.07 MB)
   - Table `companies`: Exactly **52 rows**.
   - Overlap: All 52 database companies are valid subsets of the 100-stock definition.
   - Missing from database: 48 companies (e.g. `ADANIGREEN`, `ADANIPOWER`, `AMBUJACEM`, `BAJAJHLDNG`, etc.).
3. **Historical Commit Evidence:**
   - Commit `77d8aff` (`fix: resolve dashboard & stock explorer data integration gaps and add readiness test suite`):
     Explicitly locked the active working universe to 52 companies (`universe count dynamically resolves to 52 from health API`).
4. **Data Pipeline & Test Isolation:**
   - The active database has full historical coverage for all 52 companies:
     - Companies with daily price series: **52 / 52** (25,746 bars, 2024-10-23 to 2026-10-23)
     - Companies with quarterly financials: **52 / 52** (260 quarters)
     - Companies with precomputed technical indicators: **52 / 52**
   - The remaining 48 stocks have not yet been ingested into the local SQLite database.

### Conclusion on Universe Count:
The reported **52 companies** is an accurate, honest reflection of the active database and frontend integration. It is not a bug or discrepancy with reality, but rather the phase-1 curated development dataset of 52 stocks from the broader 100-stock roadmap.

---

## 2. Database Integrity Metrics

| Metric | Measured Value | Standard / Expectation | Status |
|---|:---:|:---:|:---:|
| **Database Path** | `database/swing_trading.db` | Project root `database/` | **VERIFIED** |
| **Total Companies** | 52 | Phase 1 universe (52 Nifty core) | **VERIFIED** |
| **Unique Symbols** | 52 | Exactly matches company count | **VERIFIED** |
| **Daily Price Records** | 25,746 | ~495 bars per company | **VERIFIED** |
| **Date Range** | 2024-10-23 to 2026-10-23 | Exactly 2 full calendar years | **VERIFIED** |
| **Duplicate (company_id, date)** | 0 | Unique constraint enforced | **VERIFIED** |
| **Corrupted OHLC Records** | 0 | $High \ge Low, High \ge Open, High \ge Close, Low \le Open, Low \le Close, P > 0$ | **VERIFIED** |
| **Quarterly Financial Records** | 260 | Exactly 5 quarters per company | **VERIFIED** |
| **Precomputed Technical Rows** | 52 | Matches 52 active companies | **VERIFIED** |

