# Week 11 Monday Data Inventory Report

## WEEK 11 — DATA INVENTORY
=========================

Stock Universe:
- Expected: 50
- Available: 50

### MARKET DATA
-----------
- **Status**: PASS
- **Available**: 50/50 stocks
- **Total records**: 25,450 records
- **Latest date**: 2026-08-27T00:00:00+05:30
- **Unique trading dates**: 509
- **Issues**: Zero-volume records (252) and extreme daily movements (>20% move, 3 rows) detected and logged as warnings (non-blocking). No invalid prices (open, high, low, close <= 0) or volumes (< 0).

### FINANCIAL DATA
--------------
- **Status**: WARNING
- **Available**: 50/50 stocks
- **Total records**: 280 quarterly records
- **Quarterly data range**: 2024-12-31 to 2026-06-30 (7 unique quarters)
- **Annual data**: Not available separately (standardized to quarterly results).
- **Issues**: Missing metrics reported as warnings. Specifically:
  - Revenue missing: 32 (88.57% coverage)
  - Net Profit missing: 32 (88.57% coverage)
  - EPS missing: 33 (88.21% coverage)
  - ROE missing: 205 (26.79% coverage)
  - ROCE missing: 186 (33.57% coverage)
  - Debt/Equity missing: 32 (88.57% coverage)
  - Operating margin missing: 0 (100% coverage)
  - Net margin missing: 0 (100% coverage)
  - Negative net profit: 3 records (review warning)

### SECTOR DATA
-----------
- **Status**: PASS
- **Mapped**: 50/50 stocks
- **Total unique sectors**: 16
- **Issues**: None. All companies successfully mapped to the sector master.

### INDUSTRY DATA
-------------
- **Status**: PASS
- **Mapped**: 50/50 stocks
- **Total unique industries**: 32
- **Issues**: None. All companies successfully mapped to the industry master.

### VALIDATION SUMMARY
------------------
- **Market Data**: Passed validation (verified OHLC relationships, duplicate check, and database orphans). No gaps in trading dates compared to the reference trading calendar.
- **Financial Data**: Passed database integrity constraints (no duplicates, no orphans, UNIQUE constraint active). Missing values and negative profits are correctly flagged as warnings without blocking the pipeline.
- **Sector Data**: Passed. Mappings are consistent with the stock universe master.
- **Industry Data**: Passed. Mappings are consistent with the stock universe master.
- **Cross-Dataset Consistency**: Passed. No orphans or mismatching identifiers found across tables (`companies`, `daily_prices`, `quarterly_results`).

### KNOWN DATA GAPS
---------------
1. **Low ROE / ROCE coverage**: ROE has 26.79% coverage and ROCE has 33.57% coverage. This is a known source limitation and downstream systems must handle NULL fields.
2. **Missing financial metrics (Revenue/Profit/EPS/Debt-Equity)**: ~11-12% missing records across these metrics due to new listings (e.g., JIOFIN) or reporting timing differences.
3. **Zero-volume records**: 252 zero-volume records exist in market data. These are flagged as warning indicators.

### FINAL STATUS
------------
- **READY FOR WEEK 11 TUESDAY**: YES

---

## Technical Details

### Database Inventory
- **Database File**: `database/swing_trading.db`
- **Tables**:
  - `companies`: 50 rows
  - `daily_prices`: 25,450 rows
  - `quarterly_results`: 280 rows
  - `sectors`: 16 rows
  - `industries`: 32 rows
  - `technical_indicators`: 25,309 rows
  - `financial_scores`: 0 rows (reserved for Logic Engineer)
  - `opportunity_scores`: 0 rows (reserved for Logic Engineer)
  - `signals`: 0 rows (reserved for Logic Engine)

### Data Services & Testing
- **Test Executed**: `.venv\Scripts\python -m backend.data_pipeline.validate_all`
- **Test Result**: `PASS`
- **Verification**: Verified 5 individual stocks (`INFY`, `TCS`, `WIPRO`, `RELIANCE`, `HDFCBANK`) and the complete 50-stock universe.
