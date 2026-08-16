# Financial Data Schema

## Purpose

This document defines the standardized financial data stored by the
Data Engineering layer for the Swing Trading Intelligence Platform.

The Data Engineer is responsible for collecting, normalizing, validating,
and storing financial data.

The Logic Engineer is responsible for interpreting this data and
calculating financial scores.

---

# Data Storage

Financial data is stored in:

`quarterly_results`

Each record represents one company's financial information for one
reporting period.

---

# Fields

| Field | Type | Description |
|---|---|---|
| company_id | INTEGER | Internal company identifier |
| quarter | TEXT | Reporting period |
| revenue | REAL | Company revenue for the reporting period |
| net_profit | REAL | Company net profit |
| eps | REAL | Earnings per share |
| roe | REAL | Return on Equity |
| roce | REAL | Return on Capital Employed |
| debt_equity | REAL | Debt-to-equity ratio |
| operating_margin | REAL | Operating profit margin |
| net_margin | REAL | Net profit margin |

---

# Company Mapping

Financial records reference the `companies` table using:

`company_id`

The Data Engineer must not duplicate company names or symbols inside
the financial table.

Relationship:

```text
companies
    |
    | company_id
    v
quarterly_results