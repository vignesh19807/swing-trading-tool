# Week 4 — Red Flag Detection Rules

## A. Purpose
This document specifies the integration contract for the deterministic financial red-flag analyzer, built during Week 4 Wednesday.

**Architectural Boundary:**
- **Annual Financial Analyzer:** Computes trends (Improving, Declining, Stable) and CAGR (Compound Annual Growth Rate) for annual financial metrics.
- **Red Flag Analyzer:** Uses the existing trends to raise deterministic signals of severe deterioration.
- The Logic Engineering layer does NOT fetch, store, or persist annual financial data.

## B. Red-Flag Rules Implemented
Red flags are generated solely based on available trend data.

1. **Revenue Deterioration (`revenue_decline`)**
   - **Condition:** Raised when the `revenue_trend` is exactly `"Declining"`.
   - **Metric:** `revenue`
   - **Reason:** "Revenue shows a declining trend across the available consecutive annual periods."

2. **Net Profit Deterioration (`net_profit_decline`)**
   - **Condition:** Raised when the `net_profit_trend` is exactly `"Declining"`.
   - **Metric:** `net_profit`
   - **Reason:** "Net profit shows a declining trend across the available consecutive annual periods."

3. **ROE Weakness (`roe_decline`)**
   - **Condition:** Raised when the `roe_trend` is exactly `"Declining"`.
   - **Metric:** `roe`
   - **Reason:** "Return on Equity (ROE) shows a materially declining trend across annual periods."

4. **ROCE Weakness (`roce_decline`)**
   - **Condition:** Raised when the `roce_trend` is exactly `"Declining"`.
   - **Metric:** `roce`
   - **Reason:** "Return on Capital Employed (ROCE) shows a materially declining trend across annual periods."

5. **Negative Revenue CAGR (`negative_revenue_cagr`)**
   - **Condition:** Raised when `revenue_cagr` is mathematically negative (`< 0.0`) and the `revenue_decline` flag is not already raised.
   - **Severity:** High

6. **Negative Profit CAGR (`negative_profit_cagr`)**
   - **Condition:** Raised when `net_profit_cagr` is mathematically negative (`< 0.0`) and the `net_profit_decline` flag is not already raised.
   - **Severity:** High

## C. Missing-Data Behavior
Missing data (`None` or `"Insufficient Data"`) is strictly ignored.
- Missing Revenue → **No flag**
- Missing Net Profit → **No flag**
- Missing ROE → **No flag**
- Missing ROCE → **No flag**
- Insufficient History → Returns `{"has_red_flags": False, "red_flags": []}`.
False positives are avoided. Values are never fabricated or defaulted to zero.

## D. Output Structure
The analyzer returns a structured dictionary:
```python
{
    "has_red_flags": True,
    "red_flags": [
        {
            "type": "revenue_decline",
            "severity": "warning",
            "metric": "revenue",
            "reason": "Revenue shows a declining trend across the available consecutive annual periods."
        }
    ]
}
```

## E. Architectural Notes
- **Disclaimer:** Red flags are deterministic analysis signals. They are **NOT** investment advice.
- Missing data does **not** imply financial weakness; it simply yields no flag.
- The Logic Engineer does not fetch annual data.
- No database/schema/API/yfinance changes are being made.
