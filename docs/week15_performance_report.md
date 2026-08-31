# Week 15 — Performance & Scalability Report

**Swing Trading Intelligence Platform | Data Engineering Layer**  
**Benchmark Date**: August 31, 2026  
**Environment**: Python 3.14 / SQLite 3 / Windows 11  
**Test Suite**: `backend/data_pipeline/benchmark_performance.py`

---

## 1. Executive Summary

This report documents the performance, query execution timings, memory profiles, database index utilization, and scalability characteristics of the Data Engineering layer across the **50-stock universe** (25,495 market & technical records, 280 financial quarters).

### Key Highlights:
- **Single-Stock OHLCV Retrieval**: ~15–20 ms per stock (510 rows).
- **Latest Price Lookup**: ~3.5 ms.
- **Historical 1-Year Date Range Query**: ~9.3 ms (250 rows).
- **Technical Indicator Retrieval**: ~5.7–7.1 ms (510 rows).
- **Financial History Retrieval**: ~3.7 ms (7 quarterly periods).
- **Point-in-Time Backtest Input Construction**: ~60 ms for 1-month daily evaluation window (18 records joined across market, technical, financial, and classification tables).
- **Full 50-Stock Universe Full-Market Extraction**: ~306 ms total for all 25,495 rows.
- **Index Review (`EXPLAIN QUERY PLAN`)**: 100% of critical queries utilize composite B-tree indexes; **0 unindexed full-table scans** detected.
- **Optimization Conclusion**: **No code optimization required**. All queries perform well within interactive sub-second thresholds.

---

## 2. Benchmark Measurement Results

All operations were executed over multiple iterations with memory tracking enabled via Python `tracemalloc`.

| Operation | Target / Scope | Iterations | Avg Latency (ms) | Min (ms) | Max (ms) | Rows / Output | Peak Memory |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **Universe Discovery** | `get_available_stocks()` | 5 | **2.40 ms** | 1.72 ms | 3.86 ms | 50 stocks | 68.5 KB |
| **Single-Stock OHLCV** | `get_stock_data("INFY")` | 5 | **20.50 ms** | 15.38 ms | 38.17 ms | 510 rows | 648.7 KB |
| **Single-Stock OHLCV** | `get_stock_data("TCS")` | 5 | **15.93 ms** | 14.65 ms | 16.64 ms | 510 rows | 204.4 KB |
| **Single-Stock OHLCV** | `get_stock_data("RELIANCE")` | 5 | **16.90 ms** | 16.01 ms | 17.34 ms | 510 rows | 203.5 KB |
| **Latest Price Lookup** | `get_latest_price("INFY")` | 10 | **3.76 ms** | 3.04 ms | 5.89 ms | 1 record | 25.7 KB |
| **Latest Price Lookup** | `get_latest_price("HDFCBANK")` | 10 | **3.56 ms** | 2.95 ms | 5.43 ms | 1 record | 23.4 KB |
| **Historical 1-Year Range** | `get_stock_data("INFY", start, end)` | 5 | **9.35 ms** | 8.58 ms | 10.20 ms | 250 rows | 105.1 KB |
| **Technical Indicators** | `get_technical_indicators("INFY")` | 5 | **5.74 ms** | 4.82 ms | 7.00 ms | 510 rows | 597.1 KB |
| **Technical Indicators** | `get_technical_indicators("TCS")` | 5 | **7.10 ms** | 4.95 ms | 10.90 ms | 510 rows | 527.0 KB |
| **Financial History** | `get_financial_data("INFY")` | 5 | **3.71 ms** | 3.14 ms | 4.39 ms | 7 quarters | 35.9 KB |
| **Latest Financial Record** | `get_latest_financial_data("INFY")` | 5 | **6.86 ms** | 5.74 ms | 8.70 ms | 1 record | 25.0 KB |
| **Backtest Input Extraction** | `get_backtest_inputs("INFY", ...)` | 3 | **60.23 ms** | 56.54 ms | 66.57 ms | 18 records | 415.0 KB |
| **Backtest Input Extraction** | `get_backtest_inputs("TCS", ...)` | 3 | **61.39 ms** | 55.19 ms | 66.69 ms | 18 records | 353.2 KB |
| **Full 50-Stock Universe** | Full Market Price Extraction | 1 | **306.92 ms** | 306.92 ms | 306.92 ms | 25,495 rows | N/A |
| **Backtest Result Store** | `store_backtest_results(...)` | 1 | **18.08 ms** | 18.08 ms | 18.08 ms | 20 records | 4.8 KB |
| **Backtest Result Retrieval** | `get_backtest_results(run_id, ...)` | 5 | **2.21 ms** | 1.60 ms | 3.12 ms | 20 records | 34.8 KB |

---

## 3. Database Index Review & Query Plan Analysis

The SQLite database (`database/swing_trading.db`) contains dedicated B-tree indexes for all core query paths.

### Active Custom Indexes:
1. `idx_daily_prices_company_date` on `daily_prices(company_id, date)`
2. `idx_technical_indicators_company_date` on `technical_indicators(company_id, date)`
3. `idx_quarterly_results_company_quarter` on `quarterly_results(company_id, quarter)`
4. `idx_quarterly_results_quarter` on `quarterly_results(quarter)`
5. `idx_companies_sector_id` on `companies(sector_id)`
6. `idx_companies_industry_id` on `companies(industry_id)`
7. `idx_industries_sector_id` on `industries(sector_id)`
8. `idx_financial_scores_company_date` on `financial_scores(company_id, date)`
9. `idx_opportunity_scores_company_date` on `opportunity_scores(company_id, date)`
10. `idx_signals_company_date` on `signals(company_id, date)`
11. `idx_backtest_results_run_symbol_date` on `backtest_results(run_id, symbol, evaluation_date)`

### `EXPLAIN QUERY PLAN` Verification:

```sql
-- 1. Daily Prices by Symbol and Date Range
EXPLAIN QUERY PLAN
SELECT dp.date, dp.open, dp.high, dp.low, dp.close, dp.volume
FROM daily_prices dp
JOIN companies c ON c.id = dp.company_id
WHERE c.symbol = 'INFY' AND dp.date >= '2025-01-01'
ORDER BY dp.date ASC;
```
**Plan Output**:
- `SEARCH c USING COVERING INDEX sqlite_autoindex_companies_1 (symbol=?)`
- `SEARCH dp USING INDEX idx_daily_prices_company_date (company_id=? AND date>?)`

```sql
-- 2. Technical Indicators by Symbol
EXPLAIN QUERY PLAN
SELECT ti.*
FROM technical_indicators ti
JOIN companies c ON c.id = ti.company_id
WHERE c.symbol = 'INFY'
ORDER BY ti.date ASC;
```
**Plan Output**:
- `SEARCH c USING COVERING INDEX sqlite_autoindex_companies_1 (symbol=?)`
- `SEARCH ti USING INDEX idx_technical_indicators_company_date (company_id=?)`

```sql
-- 3. Backtest Results Lookup
EXPLAIN QUERY PLAN
SELECT *
FROM backtest_results
WHERE run_id = 'BENCHMARK_RUN' AND symbol = 'INFY'
ORDER BY evaluation_date ASC;
```
**Plan Output**:
- `SEARCH backtest_results USING INDEX idx_backtest_results_run_symbol_date (run_id=? AND symbol=?)`

---

## 4. Repeated-Query & 50-Stock Universe Memory Check

- **50-Stock Universe Processing**: Iterating over all 50 companies and loading their entire historical price history (25,495 rows) completes in **~306 milliseconds**.
- **Memory Footprint**: Peak heap allocation during single-stock data frame creation is below **700 KB**. Batch backtesting input generation consumes less than **500 KB** per stock window.
- **Repeated Query Patterns**: Single-stock calls (`get_latest_price`, `get_stock_data`) execute in < 4 ms and < 20 ms respectively. The composite index on `(company_id, date)` ensures that repeated queries remain lightweight and do not trigger lock contention or cache thrashing.

---

## 5. Performance Improvements & Before/After Observations

- **Evaluation**: The current index topology provides direct point-lookup and range-scan coverage for all production data-service query interfaces.
- **Bottleneck Analysis**: No table scans, N+1 query traps, or high-latency queries were observed in the benchmark.
- **Action Taken**: In accordance with Week 15 Rule 5, no artificial code changes were introduced because existing benchmarks already exceed the required performance standards.
