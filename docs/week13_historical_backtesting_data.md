# Week 13 — Historical & Backtesting Data Engineering

## Objective

Build a reliable historical data layer for backtesting while preserving
historical evaluation dates and preventing future-data leakage.

## Completed Components

### 1. Historical Data Service

File:

`backend/data_pipeline/historical_data_service.py`

Responsibilities:

- Retrieve historical OHLCV data.
- Support start and end dates.
- Validate stock symbols.
- Validate date format.
- Reject reversed date ranges.
- Preserve chronological ordering.
- Provide adjusted close.
- Report basic data quality.

### 2. Data Service Enhancement

File:

`backend/data_pipeline/data_service.py`

Enhanced historical retrieval to support:

- `start_date`
- `end_date`
- timezone-aware date filtering
- adjusted close retrieval

### 3. Backtesting Dataset Service

File:

`backend/data_pipeline/backtesting_dataset_service.py`

The service combines historical:

- Market data
- Technical indicators
- Financial data
- Company classification

into an evaluation-date-based dataset.

Each observation represents:

`symbol + evaluation_date`

### 4. Historical Data Contract

The dataset exposes:

- symbol
- evaluation_date
- company_name
- sector
- industry
- OHLCV data
- adjusted_close
- technical indicators
- financial data
- reporting_period
- data availability status
- leakage_check

### 5. Data Leakage Protection

Financial reporting periods are checked against the evaluation date.

A future financial period must never be used for an earlier
backtesting observation.

The current validation reports:

- future financial periods: 0
- leakage failures: 0

### 6. Technical Indicator Warm-up

Technical indicators may legitimately contain missing values during
their initial warm-up period.

These missing values are preserved rather than fabricated.

### 7. Dataset Quality Validation

The quality report checks:

- dataset status
- row count
- symbol count
- duplicate observations
- missing market data
- missing technical data
- future financial periods
- leakage failures

## Validation Results

Test symbol:

`INFY`

Test period:

`2025-08-01` to `2025-08-28`

Historical observations:

`18`

Quality result:

`VALID`

Market data missing:

`0`

Duplicate observations:

`0`

Future financial periods:

`0`

Leakage failures:

`0`

Technical warm-up observations:

`5`

The five technical-data gaps are expected warm-up observations and are
not treated as fabricated or invalid data.

## Automated Tests

Test file:

`backend/data_pipeline/test_backtesting_dataset_service.py`

Result:

`19 tests passed`

Command:

```text
python -m unittest backend.data_pipeline.test_backtesting_dataset_service -v

Result:

Ran 19 tests

OK
```
## Data Engineering Boundary

This component is responsible for preparing and validating historical
data for downstream backtesting.

It does NOT:

- generate trading signals
- make buy/sell decisions
- optimize strategies
- calculate trading returns
- evaluate strategy profitability

Those responsibilities belong to downstream logic/analysis components.

## Full Regression Validation

Command:

```text
python -m unittest discover -s backend\data_pipeline -p "test_*.py" -v

Result:

Ran 61 tests

OK
```