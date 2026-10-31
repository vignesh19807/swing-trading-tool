# AUDIT-017: Reporting Lag Sensitivity & Assumption Analysis

**Audit Identifier:** AUDIT-017-LAG-SENSITIVITY  
**Execution Timestamp:** 2026-10-29 22:17 IST  
**Auditor:** Quantitative Trading System Auditor & Test Engineer  
**Scope:** Verification of publication timestamps, eligibility rules, and sensitivity testing across 45-day, 60-day, and 90-day lag assumptions.

---

## 1. Executive Summary

In the existing SQLite database, publication timestamps are not recorded for quarterly financial results. The platform relies on a 45-day reporting lag fallback (`quarter_end_date + 45 days`).

> [!IMPORTANT]
> **Methodological Disclaimer:** The 45-day lag is an **explicit model assumption**, not an empirical record of actual corporate disclosure timestamps. This sensitivity analysis assesses model stability under varying reporting lag assumptions. It must not be cited as proof of actual disclosure timing.

---

## 2. Timestamp Inventory & Eligibility Rule Architecture

| Category | Record Count | Percentage | Operational Eligibility Rule |
| :--- | :--- | :--- | :--- |
| **Verified Publication Timestamps** | 0 | 0.0% | `publication_date <= evaluation_date` (strict point-in-time) |
| **Missing Timestamps (NULL / Empty)** | 260 | 100.0% | `quarter_end_date + reporting_lag_days <= evaluation_date` |
| **Total Quarterly Records** | 260 | 100.0% | 5 quarters $\times$ 52 companies |

### Rule Logic:
1. If `publication_date` is populated, it is normalized to UTC naive and compared directly against `evaluation_date`.
2. If `publication_date IS NULL`, the quarter end date is resolved (e.g. `2025-Q4` $\rightarrow$ `2025-12-31`). An assumed reporting lag ($L \in \{45, 60, 90\}$ days) is added to determine the earliest permissible date of observation.

---

## 3. Sensitivity Comparison Matrix

The 5-stock historical pilot (`2025-10-01` to `2026-03-31`, 610 stock-sessions) was evaluated across 45-day, 60-day, and 90-day lag assumptions:

| Lag Assumption | Effective Date of Q4 2025 | Raw BUY Recommendations | Trade Quality Rejections | Executed Trades | Net Portfolio Return | Max Drawdown |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **45 Days (Baseline)** | `2026-02-14` | **4** | **4 (100.0%)** | **0** | **0.00%** | **0.00%** |
| **60 Days (Conservative)** | `2026-03-01` | **4** | **4 (100.0%)** | **0** | **0.00%** | **0.00%** |
| **90 Days (Ultra-Conservative)**| `2026-03-31` | **4** | **4 (100.0%)** | **0** | **0.00%** | **0.00%** |

### Detailed Candidate Consistency:
Across all three lag assumptions:
1. `ITC` on `2026-02-17`: Rejected by `PRICE_OUTSIDE_ENTRY_ZONE`.
2. `ITC` on `2026-02-18`: Rejected by `PRICE_OUTSIDE_ENTRY_ZONE`.
3. `RELIANCE` on `2026-03-09`: Rejected by `PRICE_OUTSIDE_ENTRY_ZONE`.
4. `RELIANCE` on `2026-03-20`: Rejected by `INSUFFICIENT_RISK_REWARD_RATIO`.

---

## 4. Key Takeaways & Limitations

1. **Invariance of Execution Outcome:**  
   Regardless of whether a 45-day, 60-day, or 90-day lag assumption is applied, **zero trades qualified for execution**. Capital was 100% preserved in cash during the -17.53% market downturn.
2. **Strategy Robustness vs Data Limitation:**  
   The platform's execution and risk management gates (`PRICE_OUTSIDE_ENTRY_ZONE` and `INSUFFICIENT_RISK_REWARD_RATIO`) are the primary determinants of trade non-execution, providing robust defense against false signals regardless of the reporting lag parameter.
3. **PEAD Research Restriction:**  
   Post-Earnings Announcement Drift (PEAD) backtesting remains **strictly prohibited** until actual exchange announcement timestamps (NSE/BSE filings) are ingested.

