# Week 14 — Backtest Data Access Service

## Purpose
The Backtest Data Access Service provides a clean, validated data-access interface that retrieves historical stock metrics at a specific date or date range. It guarantees that downstream components (like the Logic Engine / Backtest Engine) only access historical data available as of the requested evaluation date.

## File Location
* [`backend/data_pipeline/backtest_data_access_service.py`](file:///c:/Users/vigne/OneDrive/Desktop/projects/SWING%20TOOL/swing-trading-tool1/backend/data_pipeline/backtest_data_access_service.py)
* [`backend/data_pipeline/test_backtest_data_access_service.py`](file:///c:/Users/vigne/OneDrive/Desktop/projects/SWING%20TOOL/swing-trading-tool1/backend/data_pipeline/test_backtest_data_access_service.py)

## Key Interfaces

### 1. `get_backtest_input(symbol: str, evaluation_date: str) -> Optional[dict]`
Retrieves the historical technical, financial, and market data for a single company on a single date.
* **Arguments**:
  * `symbol`: Ticker symbol (e.g., `"INFY"`).
  * `evaluation_date`: Date string in `YYYY-MM-DD` format.
* **Returns**: A dictionary containing aligned metrics or `None` if no trading record exists for that date.

### 2. `get_backtest_inputs(symbol: str, start_date: str, end_date: str) -> list[dict]`
Retrieves historical data observations for a symbol over a chronological date range.
* **Arguments**:
  * `symbol`: Ticker symbol.
  * `start_date`: Range start date (`YYYY-MM-DD`).
  * `end_date`: Range end date (`YYYY-MM-DD`).
* **Returns**: A chronological list of dictionaries, one for each trading day in the range.

## Strict Data Validation Rules
1. **Symbol Normalization**: Symbol input is trimmed, converted to uppercase, and validated for non-emptiness.
2. **Date Format Validation**: Dates must match the `YYYY-MM-DD` pattern and represent valid calendar dates.
3. **Future-Date Protection**: Rejects evaluation dates that are in the future relative to the system's current local date.
4. **Range Integrity**: Ensures that the start date is less than or equal to the end date.
5. **No-Leakage Policy**: Financial reporting periods and technical indicators are matched point-in-time strictly based on the active evaluation date. Future information (e.g., quarterly results released after the evaluation date) is never included in the input record.
