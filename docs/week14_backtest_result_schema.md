# Week 14 — Backtest Result Schema

## Table Definition
Backtest results are persisted in the SQLite database under the `backtest_results` table.

```sql
CREATE TABLE IF NOT EXISTS backtest_results (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id TEXT NOT NULL,
    symbol TEXT NOT NULL,
    evaluation_date TEXT NOT NULL,
    result_metadata TEXT NOT NULL, -- JSON string containing run strategy output
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(run_id, symbol, evaluation_date)
);
```

## Schema Constraints
1. **Uniqueness**: Composite unique constraint `UNIQUE(run_id, symbol, evaluation_date)` prevents duplicate entries for the same stock and evaluation date within a single backtest run.
2. **Nullable Rules**: `run_id`, `symbol`, `evaluation_date`, and `result_metadata` are enforced as `NOT NULL`.

## Performance Indexes
An index is automatically generated to optimize queries filtering by run, stock, and date range:
```sql
CREATE INDEX IF NOT EXISTS idx_backtest_results_run_symbol_date
ON backtest_results(run_id, symbol, evaluation_date);
```

## Metadata Storage
The `result_metadata` column stores JSON string data containing downstream backtest strategy outputs. This separates concerns, ensuring that the Data Engineering layer can validate, store, and retrieve results without needing to hardcode strategy-specific metrics.
Example structure stored inside `result_metadata`:
```json
{
  "technical_score": 75.0,
  "financial_score": 60.0,
  "momentum_score": 83.33,
  "opportunity_score": 69.83,
  "recommendation": "BUY"
}
```
