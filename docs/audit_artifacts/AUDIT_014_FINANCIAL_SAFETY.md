# AUDIT-014: Point-in-Time Financial Safety, Publication Provenance & Lookahead Limitations

**Project:** Swing Trading Intelligence Platform — Indian Equities  
**Module Inspected:** `backend/data_pipeline/financial_service.py`  
**Database Table Inspected:** `quarterly_results` (52 companies, 260 quarterly records)  
**Verification Date:** 2026-10-29  
**Status:** **LOOKAHEAD PROTECTED VIA CONSERVATIVE FALLBACK — REAL PUBLICATION TIMESTAMPS REQUIRED FOR STRICT BACKTESTING**

---

## 1. Active Database Empirical Investigation

Direct SQL schema and data inspection of the active SQLite database (`database/swing_trading.db`) reveals a critical empirical reality:
- **Total Rows in `quarterly_results`:** 260 rows (5 quarters across 52 stocks).
- **Rows with Valid `publication_date`:** **0 rows (0.0%)**.
- **Rows with `NULL` `publication_date`:** **260 rows (100.0%)**.

### Architectural Consequence:
Because all 260 rows in the active database currently contain `NULL` publication dates, **every historical financial lookup in the active system relies exclusively on the 45-day statutory fallback heuristic**.

---

## 2. Actual Publication Date vs 45-Day Fallback Heuristic

It is vital to distinguish between **actual market availability** and **conservative model gating**:

1. **What the 45-Day Fallback Is:**
   - Under SEBI LODR Regulation 33(3)(a), listed Indian companies must submit quarterly financial results to the exchanges within 45 days of the close of each quarter.
   - The platform calculates eligibility as:
     $$\text{Eligibility Timestamp} = \text{Quarter Period End} + 45 \text{ days}$$
   - For example, for Q3 ending `2024-12-31`, the fallback date is `2025-02-14 23:59:59`.
2. **What the Fallback Proves:**
   - It proves that **no forward information can leak backwards**. Because 45 days is the legal deadline, results are guaranteed to have been disclosed on or before day 45.
   - It acts as an absolute lookahead safety barrier.
3. **What the Fallback Does NOT Prove:**
   - **It does NOT prove actual publication timing.** Large-cap companies like TCS and Infosys routinely report within 10 to 18 days of quarter-end (e.g., mid-January for the December quarter). The 45-day fallback artificially delays the availability of their fundamentals by approximately 30 days.
   - Therefore, claims that the current dataset provides "true point-in-time fidelity" are false. It provides **conservative lookahead immunity**, but not historical publication timing.

---

## 3. Code Inspection: Gating Mechanics & Edge-Case Vulnerabilities

In `backend/data_pipeline/financial_service.py:182-320`:

```python
for idx, row in data.iterrows():
    q_val = row.get("quarter")
    pub_val = row.get("publication_date")

    period_end = parse_quarter_period_end(q_val)
    if period_end is None:
        continue

    if pd.notna(pub_val) and str(pub_val).strip():
        # Branch 1: Explicit publication date gating
        pub_ts = pd.to_datetime(str(pub_val).strip())
        if pub_ts <= eval_ts:
            eligible_indices.append(idx)
            statuses[idx] = "VERIFIED_POINT_IN_TIME"
            verified_flags[idx] = True
    else:
        # Branch 2: Conservative fallback lag under SEBI LODR Reg 33
        lag = max(0, int(reporting_lag_days)) if reporting_lag_days is not None else 45
        avail_ts = period_end + pd.Timedelta(days=lag)
        if avail_ts <= eval_ts:
            eligible_indices.append(idx)
            statuses[idx] = "PERIOD_ELIGIBLE_FALLBACK_LAG"
            verified_flags[idx] = False
```

### Edge-Case & Boundary Analysis:
1. **Precedence:** Explicit publication dates (`pub_val`) take absolute precedence over the fallback.
2. **Date-Only vs Timestamp Semantics:** Lines 275-276 convert date strings (`YYYY-MM-DD`) to end-of-day timestamps (`23:59:59.999999`), ensuring that an evaluation on `2025-02-14` correctly includes results published during market hours on that day.
3. **Timezone Pitfall (Latent Risk):** `parse_quarter_period_end` returns a tz-naive Timestamp (`p.end_time`). If an upstream caller supplies a timezone-aware ISO string (e.g., `2025-02-14T15:30:00+05:30`), `pd.to_datetime` produces a tz-aware object, causing pandas to raise `TypeError: Cannot compare tz-naive and tz-aware timestamps`. At present, all internal callers pass standard YYYY-MM-DD strings, avoiding this error.

---

## 4. Evaluation of Existing Test Suites

The platform contains 15 tests across `test_audit_001_financial_lookahead.py` and `test_historical_financial_safety.py`:
- **What These Tests Prove:**
  - They prove that the filtering logic in `get_latest_financial_data` functions as designed: it correctly rejects records whose publication date or 45-day fallback post-dates the evaluation date.
  - They prove that future earnings cannot retroactively alter earlier historical valuations.
- **What These Tests Do NOT Prove:**
  - They do **not** prove that the live production database contains real corporate announcement dates.
  - They do **not** validate that real market traders had access to fundamentals at the exact historical moment the model assumes.

---

## 5. Decision on Backtest Feasibility

### Can the existing 260 records support a strict point-in-time backtest?
- **For Conservative / Safety-Oriented Historical Testing:** **YES**. Because the 45-day lag delays availability rather than accelerating it, any backtest run on the current database will be conservative. It will never cheat or overestimate performance due to fundamental lookahead.
- **For Strict Institutional Quality / Production Grade:** **NO**. To evaluate earnings momentum or post-earnings announcement drift (PEAD) accurately, the database must be enriched with true exchange filing timestamps (`publication_date`) from NSE/BSE corporate filings.

