# Week 11 — Validated Data Inventory

## Purpose

This document records the validated datasets available to the
Week 11 integrated Data Engineering layer.

Week 10 validation is the source of truth for dataset integrity.

---

## 1. Market Data

Source table:

- `daily_prices`

Access service:

- `backend.data_pipeline.data_service`

Primary access:

- `get_stock_data(symbol)`

Required fields:

- date
- open
- high
- low
- close
- volume

Week 10 status:

- 50/50 stocks available
- 25,300 market records
- No duplicate records
- No orphan records
- No missing critical OHLCV values

Status:

- VALIDATED

---

## 2. Financial Data

Source table:

- `quarterly_results`

Access service:

- `backend.data_pipeline.financial_service`

Primary access:

- `get_financial_data(symbol)`
- `get_latest_financial_data(symbol)`

Required fields:

- revenue
- net_profit
- eps
- roe
- roce
- debt_equity
- operating_margin
- net_margin

Week 10 status:

- 50/50 companies have financial records
- 280 financial records
- No duplicate company/quarter records
- No orphan records
- Missing source values remain NULL

Known warnings:

- Revenue missing: 32
- Net profit missing: 32
- EPS missing: 33
- ROE missing: 205
- ROCE missing: 186
- Debt/Equity missing: 32
- Negative net-profit records: 3

Status:

- VALIDATED WITH KNOWN WARNINGS

---

## 3. Company Classification

Source:

- `companies`

Access service:

- `classification_service.py`

Provides:

- symbol
- company name
- sector
- industry

Week 10 status:

- 50/50 companies classified
- No missing sectors
- No missing industries
- No duplicate symbols
- STOCK_UNIVERSE mappings match database

Status:

- VALIDATED

---

## 4. Technical Data

Source:

- `technical_indicators`

Access service:

- `technical_indicator_service.py`

Provides:

- RSI
- MACD
- signal
- EMA20
- EMA50
- EMA200
- histogram
- ATR14
- technical score

Status:

- Available through the existing Technical Data Service

---

## 5. Entry / Exit Inputs

Access service:

- `entry_exit_input_service.py`

Purpose:

Provides market and technical inputs required by downstream
entry/exit logic.

The service must expose input data only.

It must not generate trading decisions.

---

## 6. Stop / Target Inputs

Access service:

- `stop_target_input_service.py`

Purpose:

Provides ATR and support/resistance inputs for downstream
stop/target logic.

It must not generate BUY/SELL decisions.

Missing inputs must remain explicitly represented.

---

## 7. Peer Groups

Access service:

- `peer_group_service.py`

Provides:

- sector peers
- industry peers
- sector summaries
- industry summaries

Week 7 validation:

- classification handoff passed
- peer-group handoff passed
- 50-company coverage verified

---

## 8. Validation Status

Week 10 validation command:

```powershell
python -m backend.data_pipeline.validate_all