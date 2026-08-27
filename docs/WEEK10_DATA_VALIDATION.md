# Week 10 — Data Validation & Reliability

## Purpose

Week 10 establishes a repeatable validation layer for the
50-stock Swing Trading Intelligence Platform.

The Data Engineer validates data quality before downstream
Logic Engine consumption.

---

## Validation Pipeline

```
Data Sources
    ↓
Collection
    ↓
Normalization
    ↓
Validation
    ↓
Quality Report
    ↓
Database
    ↓
Data Services
    ↓
Logic Engine
```

---

## Validation Command

Run:

```powershell
python -m backend.data_pipeline.validate_all
```

For the complete data-update + validation workflow:

```powershell
python -m backend.data_pipeline.run_pipeline
```

## Validation Rules

### Company Universe

Expected universe:
- 50 stocks

Validation:
- All expected stocks must exist.
- Duplicate symbols are not allowed.
- Company identifiers must resolve correctly.

### Market Data

Required fields:
- date
- open
- high
- low
- close
- volume

Rules:
- OHLCV fields cannot be NULL.
- Prices must be positive.
- Volume cannot be negative.
- Low <= Open <= High.
- Low <= Close <= High.
- Duplicate (company_id, date) records are not allowed.
- Market records must map to valid companies.
- Unexpected trading-date gaps are reported.
- Suspicious zero-volume records are warnings.
- Extreme daily price movements are warnings unless invalid.

Source records are not silently deleted by validation.

### Financial Data

Required fields:
- revenue
- net_profit
- eps
- roe
- roce
- debt_equity
- operating_margin
- net_margin

Rules:
- Company mapping must be valid.
- Reporting periods must be valid.
- Duplicate (company_id, quarter) records are not allowed.
- UNIQUE(company_id, quarter) is enforced.
- Orphan records are not allowed.
- Invalid numeric values cause validation failure.
- Missing values are warnings when permitted by the source.
- Negative net profit is treated as a review warning.

### Sector / Industry

Rules:
- All 50 companies must have valid mappings.
- Sector must resolve to the sector master.
- Industry must resolve to the industry master.
- Duplicate company symbols are not allowed.
- STOCK_UNIVERSE mappings must match database mappings.

### Cross-Dataset Validation

The following are checked:
- Company IDs across related tables
- Symbol/company mapping
- Market → company mapping
- Financial → company mapping
- Sector/industry mappings
- Orphan records
- Conflicting mappings
- Data-service compatibility

---

## PASS / WARNING / FAIL

### PASS
All blocking validation rules pass. The dataset can be consumed by downstream services.

### WARNING
The dataset contains known quality limitations that do not invalidate the entire dataset.

Examples:
- Missing financial metrics
- Negative net profit
- Zero-volume records
- Extreme price movement

Warnings must remain visible to downstream users.

### FAIL
A blocking integrity rule has failed.

Examples:
- Missing company mapping
- Duplicate company-period records
- Orphan records
- Invalid OHLC relationships
- Invalid non-positive prices

A failed validation means the dataset requires review before being considered trusted.

---

## Known Financial Data Limitations

Current validation reports:
- 280 financial records
- Revenue missing: 32
- Net profit missing: 32
- EPS missing: 33
- ROE missing: 205
- ROCE missing: 186
- Debt/Equity missing: 32
- Operating margin missing: 0
- Net margin missing: 0
- Negative net-profit records: 3

Missing values are preserved as NULL and reported as warnings. They are not replaced with arbitrary values.

---

## Duplicate Handling

Financial records use:
- UNIQUE(company_id, quarter)

Market records use duplicate detection for:
- (company_id, date)

Validation reports duplicate records rather than silently deleting source data.

---

## Orphan Handling

Market and financial records must reference an existing company. Orphan records cause validation failure. No orphan records are currently present.

---

## Validation Logs

Validation execution logs are stored in:
- `reports/week10_validation.log`

Quality reports are stored in:
- `reports/`

---

## Logic Engineer Handoff

The Logic Engineer should consume validated data through Data Services instead of direct SQL.

Market data:
- `get_stock_data(symbol)`

Financial data:
- `get_financial_data(symbol)`

The Week 10 handoff tests verify that the required data structure is available to downstream logic.

---

## Secrets

API keys and credentials must not be committed to Git. Environment variables and `.env` files must remain excluded from version control.

---

## Week 10 Completion

The Week 10 pipeline is complete when:
- All 50 companies validate.
- Market data validates.
- Financial data validates.
- Sector/industry mappings validate.
- Duplicate records are controlled.
- Orphan records are controlled.
- Financial uniqueness is enforced.
- Cross-dataset consistency passes.
- Validation logs are produced.
- Validation runs automatically after updates.
- Data-service handoff passes.
- Documentation is updated.
