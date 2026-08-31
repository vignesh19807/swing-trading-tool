# Week 15 — Data Service Reliability & Contract Specification

**Swing Trading Intelligence Platform | Data Engineering Layer**  
**Specification Version**: 1.0.0 (Week 15)  
**Test Suite**: `backend/data_pipeline/test_week15_service_reliability.py` (19/19 passing)

---

## 1. Overview & Service Architecture

The Data Engineering layer provides a clean, decoupled interface between raw SQLite storage and downstream consumer engines (Technical Engine, Financial Engine, Decision Engine, and Backtest Engine).

```
┌─────────────────────────────────────────────────────────────┐
│                    Downstream Consumers                     │
│   Logic Engine   •   Backtest Engine   •   API / Dashboard  │
└──────────────────────────────┬──────────────────────────────┘
                               │ Clean Data Contracts
┌──────────────────────────────▼──────────────────────────────┐
│                   Data Services Layer                       │
│  • data_service.py              • financial_service.py      │
│  • technical_indicator_service  • classification_service.py │
│  • backtest_data_access_service • backtest_result_service   │
│  • entry_exit_input_service     • stock_snapshot_service    │
└──────────────────────────────┬──────────────────────────────┘
                               │ Optimized Parameterized Queries
┌──────────────────────────────▼──────────────────────────────┐
│                    SQLite Database Layer                    │
│   companies • daily_prices • technical_indicators           │
│   quarterly_results • sectors • industries • backtest_res   │
└─────────────────────────────────────────────────────────────┘
```

---

## 2. Major Data Service Entry Points & Schema Contracts

### 2.1 Market Data Service (`backend.data_pipeline.data_service`)

| Function | Input Parameters | Return Type | Guarantees |
| :--- | :--- | :--- | :--- |
| `get_stock_data(symbol, start_date=None, end_date=None)` | `symbol: str`, optional `start_date`, `end_date` | `pd.DataFrame` (`date`, `open`, `high`, `low`, `close`, `volume`) | Chronologically ascending, normalized datetime index, returns empty DataFrame on invalid/missing symbol. |
| `get_stock_data_with_adjusted_close(symbol, ...)` | `symbol: str`, optional dates | `pd.DataFrame` (includes `adjusted_close`) | Standardized numeric columns, empty on missing. |
| `get_latest_price(symbol)` | `symbol: str` | `dict` or `None` | Point-in-time latest record, returns `None` if symbol missing. |
| `get_available_stocks()` | None | `pd.DataFrame` (`symbol`, `company_name`, `sector`, `industry`, `exchange`) | Sorted by symbol, returns all active universe companies. |
| `get_stock_record_count(symbol)` | `symbol: str` | `int` | Exact count of price records for symbol. |

### 2.2 Technical Indicator Service (`backend.data_pipeline.technical_indicator_service`)

| Function | Input Parameters | Return Type | Guarantees |
| :--- | :--- | :--- | :--- |
| `get_technical_indicators(symbol)` | `symbol: str` | `pd.DataFrame` (`symbol`, `date`, `rsi`, `macd`, `macd_signal`, `ema_20`, `ema_50`, `ema_200`, `macd_histogram`, `atr_14`, `technical_score`) | 1:1 row synchronization with market data dates; chronological ascending. |
| `get_latest_technical_indicators(symbol)` | `symbol: str` | `dict` or `None` | Most recent technical record as dictionary. |
| `save_technical_indicators(symbol)` | `symbol: str` | `int` (records processed) | Idempotent upsert via `ON CONFLICT(company_id, date) DO UPDATE`. |

### 2.3 Financial Data Service (`backend.data_pipeline.financial_service`)

| Function | Input Parameters | Return Type | Guarantees |
| :--- | :--- | :--- | :--- |
| `get_financial_data(symbol)` | `symbol: str` | `pd.DataFrame` (`symbol`, `company_name`, `sector`, `industry`, `quarter`, `revenue`, `net_profit`, `eps`, `roe`, `roce`, `debt_equity`, `operating_margin`, `net_margin`) | Standardized column order; missing fields preserved as `NaN`; never replaces missing with zero. |
| `get_latest_financial_data(symbol)` | `symbol: str` | `dict` or `None` | Database-level `ORDER BY quarter DESC LIMIT 1`; missing values typed as float `NaN`. |
| `get_financial_stocks()` | None | `List[str]` | List of distinct stock symbols with financial data. |
| `get_financial_record_count(symbol)` | `symbol: str` | `int` | Number of quarterly records available. |

### 2.4 Company Classification & Peer Group Service (`backend.data_pipeline.classification_service` & `peer_group_service`)

| Function | Input Parameters | Return Type | Guarantees |
| :--- | :--- | :--- | :--- |
| `get_company_classification(symbol)` | `symbol: str` | `dict` (`symbol`, `company_name`, `sector`, `industry`) or `None` | Resolved through foreign keys to master `sectors` and `industries` tables. |
| `get_sector_stocks(sector)` | `sector: str` | `List[str]` | Sorted list of symbols in the sector. |
| `get_industry_stocks(industry)` | `industry: str` | `List[str]` | Sorted list of symbols in the industry. |
| `get_peer_group(symbol)` | `symbol: str` | `dict` (`symbol`, `sector`, `industry`, `sector_peers`, `industry_peers`) or `None` | Reusable peer group mapping. |

### 2.5 Backtest Data Access Service (`backend.data_pipeline.backtest_data_access_service`)

| Function | Input Parameters | Return Type | Guarantees |
| :--- | :--- | :--- | :--- |
| `get_backtest_input(symbol, evaluation_date)` | `symbol: str`, `evaluation_date: str` (`YYYY-MM-DD`) | `dict` or `None` | Validates date format; rejects future dates; enforces `reporting_period <= evaluation_date`. |
| `get_backtest_inputs(symbol, start_date, end_date)` | `symbol: str`, `start_date: str`, `end_date: str` | `List[Dict[str, Any]]` | Chronological list of point-in-time rows; validates `start_date <= end_date`; zero leakage. |

### 2.6 Backtest Result Persistence Service (`backend.data_pipeline.backtest_result_service`)

| Function | Input Parameters | Return Type | Guarantees |
| :--- | :--- | :--- | :--- |
| `store_backtest_result(run_id, symbol, evaluation_date, result_metadata)` | `run_id: str`, `symbol: str`, `evaluation_date: str`, `result_metadata: dict` | `bool` | Idempotent transaction; rejects duplicates via `UNIQUE(run_id, symbol, evaluation_date)`. |
| `store_backtest_results(results)` | `List[Dict[str, Any]]` | `int` (inserted count) | Atomic batch commit; validates required schema fields on each element. |
| `get_backtest_results(run_id=None, symbol=None, start_date=None, end_date=None)` | Optional filters | `List[Dict[str, Any]]` | Dynamic parameterization; deserializes JSON metadata; indexed search. |

---

## 3. Reliability & Edge Case Handling Matrix

| Scenario | Service Behavior | Return Value / Exception | Test Status |
| :--- | :--- | :--- | :---: |
| **Non-Existent Symbol** | Graceful handling without unhandled exception | Empty `DataFrame`, `None`, or `[]` | ✅ Verified |
| **Empty Symbol String / None** | Explicit parameter validation | `ValueError: Symbol must be a non-empty string.` | ✅ Verified |
| **Malformed Date String** | Regex & datetime calendar validation | `ValueError: Invalid date format '<str>'. Expected YYYY-MM-DD.` | ✅ Verified |
| **Inverted Date Range** | Date comparison check | `ValueError: start_date '<start>' cannot be after end_date '<end>'.` | ✅ Verified |
| **Future Evaluation Date** | Compare against local system date | `ValueError: Evaluation date '<date>' is in the future.` | ✅ Verified |
| **Missing Optional Financial Metrics** | Preserves `NaN` / `None` | Returns standardized schema with `None` values (no false zeros) | ✅ Verified |
| **Batch Multi-Stock Failure** | Isolated per-stock `try...except` | Successful stocks return data; failed stocks return `data_quality: INVALID` | ✅ Verified |
| **Duplicate Backtest Insertion** | Handled via SQLite constraint | Rollback transaction, return `False` or catch duplicate safely | ✅ Verified |

---

## 4. Verification Summary

All 19 test cases in `backend/data_pipeline/test_week15_service_reliability.py` execute and pass in under 250 milliseconds, confirming schema stability, error messaging, and edge-case isolation across the Data Engineering boundary.
