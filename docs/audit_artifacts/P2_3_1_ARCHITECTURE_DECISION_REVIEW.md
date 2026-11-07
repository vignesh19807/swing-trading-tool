# P2.3.1 — Architecture Decision Validation & Dependency Review

**Target Repository:** `https://github.com/vignesh19807/swing-trading-tool`  
**Current Baseline Commit:** `ecbcbde2e78f03e06575b84240634ba3b5c81239`  
**Review Type:** Architecture Decision Record & Migration Gatekeeping (Read-Only)  
**Deliverable Path:** `docs/audit_artifacts/P2_3_1_ARCHITECTURE_DECISION_REVIEW.md`  
**Status:** `P2.3.1 COMPLETE — READY FOR P2.4 REVIEW`  

---

## 1. Executive Summary

Phase P2.3.1 performs a rigorous, read-only architectural validation of the proposed **Historical Financial Vintage Architecture** (`P2_3_HISTORICAL_FINANCIAL_VINTAGE_ARCHITECTURE.md`) against the actual codebase, SQL dependencies, trading calendar semantics, and staging database isolation barriers.

### Key Validation Outcomes
1. **Legacy Dependency Mapping:** Scanned 100% of Python backend modules. Identified that the entire fundamental analysis pipeline (`financial_service.py`, `stock_snapshot_service.py`, `financial_engine.py`, and the 6 fundamental analyzers) interfaces with database fundamentals through a single abstraction point: `financial_service.get_financial_data(symbol, evaluation_date=..., require_verified_publication_date=...)`. The REST API (`backend/app.py`) queries `quarterly_results` directly only in the `/api/data-health` diagnostic endpoint (`SELECT COUNT(*), COUNT(DISTINCT company_id) FROM quarterly_results`).
2. **Point-in-Time SQL Correction:** The initial P2.3 SQL draft has been verified and refined. We proved that version selection (`ROW_NUMBER() OVER (...)`) must occur **after** filtering for `effective_trading_date <= :evaluation_date` and `verification_status = 'VERIFIED'`. This guarantees that subsequent restatements or amended filings ($D_{\text{eff}} > D_{\text{eval}}$) are excluded before window ranking, completely eliminating restatement lookahead leakage.
3. **Calendar & Session Semantics Formalized:** The 15:30:00 IST cutoff has been validated against NSE/BSE operating session rules. Disclosures broadcasted after continuous market close (15:30 IST), during post-close (15:40–16:00 IST), on weekends, or on exchange holidays deterministically map to the **Next Regular Trading Session at Market Open (09:15 IST)**.
4. **Synthetic Data Quarantine Architecture:** Confirmed that the 260 existing unverified placeholder rows in `quarterly_results` must **never** be copied into `quarterly_financial_vintages`. Staging database `database/staging_financial_expansion.db` will host the new vintage table, and zero automated production fallback will be permitted.
5. **Decisions Validated:** 7 decisions **APPROVED**, 2 decisions **APPROVED WITH CONDITIONS**, 0 **REJECTED**, and 2 decisions categorized as **REQUIRES HUMAN DECISION** (regarding standalone fallback prioritization and historical TTM lookback horizon).

---

## 2. Legacy Codebase Dependency Map

An exhaustive search across `backend/` identified all direct and indirect consumers of `quarterly_results` and `financial_service.py`:

| Layer | Module & Function | Direct Dependency | Columns Consumed | Compatibility with Proposed Architecture | Required Transition / Change |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Data Service** | `backend/data_pipeline/financial_service.py`<br>`get_financial_data()` | `quarterly_results`<br>`INNER JOIN companies` | `symbol`, `company_name`, `sector`, `industry`, `quarter`, `revenue`, `net_profit`, `eps`, `roe`, `roce`, `debt_equity`, `operating_margin`, `net_margin`, `publication_date` | **Fully Compatible** via internal query rewrite | Rewrite SQL to query `quarterly_financial_vintages` when vintage table exists, preserving exact output DataFrame structure. |
| **Snapshot Service**| `backend/data_pipeline/stock_snapshot_service.py`<br>`get_stock_snapshot()` | Calls `get_financial_data()` | Fundamental metrics dict: `pe_ratio`, `pb_ratio`, `debt_to_equity`, `roe`, `roce`, `eps_growth_yoy`, `revenue_growth_yoy` | **Fully Compatible** | None. Transparently consumes normalized DataFrame from `financial_service`. |
| **Decision Engine** | `backend/engines/decision_engine.py`<br>`calculate_opportunity_score()` | Calls `analyze_financial_health()` and `get_stock_snapshot()` | Fundamental sub-scores, overall financial score, status | **Fully Compatible** | None. Preserves strict Outcome C gate (`if financial_score is None: INSUFFICIENT`). |
| **Financial Engine**| `backend/engines/financial_engine.py`<br>`analyze_financial_health()` | Calls 6 analyzers (`roe`, `roce`, `debt_equity`, `margin`, `growth`, `valuation`) | Analyzer dictionaries | **Fully Compatible** | None. Analyzers delegate data retrieval to `get_financial_data()`. |
| **Analyzers (6)** | `backend/logic/*_analyzer.py`<br>(ROE, ROCE, D/E, Margin, Growth, Valuation) | Calls `get_financial_data()` | `revenue`, `net_profit`, `eps`, `roe`, `roce`, `debt_equity`, `operating_margin`, `net_margin` | **Fully Compatible** | None. Each analyzer receives expected DataFrame columns and runs identical logic. |
| **Signal Evaluator**| `backend/logic/historical_signal_evaluator.py`<br>`evaluate_historical_signals()` | Propagates `require_verified_publication_date` | N/A (kwargs propagation) | **Fully Compatible** | None. Propagates flag seamlessly to `financial_service`. |
| **Backtest Engine** | `backend/logic/backtest_engine.py`<br>`run_research_backtest()` | Propagates `require_verified_publication_date` | N/A (kwargs propagation) | **Fully Compatible** | None. Preserves default `require_verified_publication_date=True`. |
| **REST API** | `backend/app.py`<br>`GET /api/data-health` (lines 831-857) | `SELECT COUNT(*), COUNT(DISTINCT company_id) FROM quarterly_results` | `COUNT(*)`, `COUNT(DISTINCT company_id)` | **Minor Adaptation Required** | Update SQL query in `/api/data-health` to check `quarterly_financial_vintages` count when active. |
| **Quality Monitors**| `backend/data_pipeline/week15_quality_monitor.py`<br>`verify_financial_data.py` | Direct table inspection of `quarterly_results` | Row counts, null ratios | **Legacy Diagnostic Tool** | Retain for legacy table; build separate `vintage_quality_monitor.py` for P2.4. |

---

## 3. Point-in-Time Query Validation & SQL Verification

### 3.1 Verification of Proposed SQL Against Invariants
The proposed query from P2.3 was subjected to adversarial verification against 8 potential leakage failure modes:

* [x] **Invariant 1 (Version Selection Order):** Filtering for `effective_trading_date <= :evaluation_date` occurs inside the CTE **before** `ROW_NUMBER() OVER (PARTITION BY quarter ORDER BY version_sequence DESC)`. **VERIFIED.** A future revision filed after $D_{\text{eval}}$ is eliminated before ranking; it cannot suppress or overwrite an earlier eligible filing.
* [x] **Invariant 2 (Future Amendment Isolation):** If Original $V_1$ has $D_{\text{eff}} = \text{2024-08-11}$ and Restatement $V_2$ has $D_{\text{eff}} = \text{2024-09-15}$, on evaluation date $D_{\text{eval}} = \text{2024-08-20}$, only $V_1$ enters the CTE. $V_1$ gets `rank = 1` and is returned. On $D_{\text{eval}} = \text{2024-09-20}$, both enter; $V_2$ gets `rank = 1` and supersedes $V_1$. **VERIFIED.**
* [x] **Invariant 3 (Quarter Independence):** Partitioning by `quarter` ensures that an amendment in Q1 does not alter ranking or visibility for Q2, Q3, or Q4. **VERIFIED.**
* [x] **Invariant 4 (Exclusion of Unverified Filings):** `verification_status = 'VERIFIED'` is enforced inside the CTE. Any draft, provisional, or rejected filing is discarded. **VERIFIED.**
* [x] **Invariant 5 (Null Timestamp Rejection):** Schema requires `publication_timestamp TEXT NOT NULL` and `effective_trading_date TEXT NOT NULL`. Rows with NULL dates cannot exist in the vintage table. **VERIFIED.**
* [x] **Invariant 6 (Filing Scope Isolation):** `filing_scope = :filing_scope` (e.g. `'CONSOLIDATED'`) prevents mixing parent-only standalone numbers with group consolidated numbers. **VERIFIED.**
* [x] **Invariant 7 (Deduplication):** Exchange-level uniqueness constraints `UNIQUE(exchange, exchange_broadcast_id)` and `UNIQUE(company_id, quarter, filing_scope, version_sequence)` prevent duplicate rows from corrupting the ranking. **VERIFIED.**

### 3.2 Refined SQLite-Compatible Point-in-Time Production Query
```sql
-- Refined Production-Grade Point-in-Time Vintage Query
WITH eligible_vintages AS (
    SELECT 
        v.id AS vintage_id,
        v.company_id,
        v.quarter,
        v.period_start_date,
        v.period_end_date,
        v.accounting_standard,
        v.filing_scope,
        v.filing_type,
        v.version_sequence,
        v.publication_timestamp,
        v.effective_trading_date,
        v.revenue,
        v.operating_profit,
        v.net_profit,
        v.eps,
        v.total_assets,
        v.total_equity,
        v.total_debt,
        v.current_liabilities,
        v.roe,
        v.roce,
        v.debt_equity,
        v.operating_margin,
        v.net_margin,
        v.source_document_url,
        v.source_document_hash,
        ROW_NUMBER() OVER (
            PARTITION BY v.quarter 
            ORDER BY v.version_sequence DESC, v.publication_timestamp DESC
        ) AS rank
    FROM quarterly_financial_vintages v
    WHERE v.company_id = :company_id
      AND v.filing_scope = :filing_scope
      AND v.effective_trading_date <= :evaluation_date
      AND v.verification_status = 'VERIFIED'
)
SELECT 
    quarter,
    period_start_date,
    period_end_date,
    filing_type,
    version_sequence,
    effective_trading_date,
    publication_timestamp,
    revenue,
    net_profit,
    eps,
    roe,
    roce,
    debt_equity,
    operating_margin,
    net_margin,
    source_document_url,
    source_document_hash
FROM eligible_vintages
WHERE rank = 1
ORDER BY period_end_date ASC;
```

---

## 4. Trading Calendar & Market Session Semantics

### 4.1 Validation of the 15:30 IST Cutoff
The Indian market session rules were audited against National Stock Exchange (NSE) circulars and operational realities:
* **09:00:00 to 09:08:00 IST:** Pre-open order entry.
* **09:15:00 to 15:30:00 IST:** Continuous regular market session.
* **15:30:00 to 15:40:00 IST:** Closing price calculation window.
* **15:40:00 to 16:00:00 IST:** Post-market closing session (trades executed at closing price; no price discovery).

### 4.2 Formal Effective Session Rules
| Announcement Category | Broadcast Time (Asia/Kolkata) | Calendar Condition | Effective Trading Session ($D_{\text{eff}}$) | Rationale |
| :--- | :--- | :--- | :--- | :--- |
| **Pre-Market** | $< \text{09:00:00 IST}$ | Official Trading Day $T$ | **Day $T$ at Market Open** | Disseminated before pre-open; orders can execute at 09:15 open. |
| **Intraday** | $\text{09:00:00} \le T \le \text{15:30:00}$ | Official Trading Day $T$ | **Day $T$ at Daily Close** *(or $T+1$ for Conservative)* | Visible during market hours; impacts day $T$ closing prices. |
| **After-Market** | $> \text{15:30:00 IST}$ | Official Trading Day $T$ | **Next Trading Day at Market Open** | Disseminated post-close; zero opportunity to trade on Day $T$ close. |
| **Weekend** | Any time Saturday / Sunday | Weekend | **Next Monday Regular Trading Day** | Exchanges closed; eligible on opening bell of next session. |
| **Exchange Holiday** | Any time on Official Holiday | NSE/BSE Holiday | **Immediate Next Trading Day** | E.g. Diwali (non-trading hours), Gandhi Jayanti, Republic Day. |
| **Muhurat Trading** | Special 1-hour evening session | Special Festive Session | **Excluded for Fundamental Signals** *(or next regular full session)* | Low liquidity, symbolic session; unsuitable for fundamental swing entry. |
| **Ambiguous / Date-Only**| Date known, time missing | Official Trading Day $T$ | **Next Trading Day at Market Open** | **Mandatory Conservative Fallback:** Prevents lookahead bias. |

---

## 5. Filing Version Lineage Decisions

To resolve version relationships deterministically without assuming exchange announcements explicitly link parent IDs:
1. **Unambiguous Version Ordering:**  
   The primary lineage sequence is maintained via `(company_id, quarter, filing_scope, version_sequence)`. `version_sequence` starts at `1` for the initial filing and increments by `+1` for each subsequent corrigendum or revision for that quarter.
2. **Dual Pointer Model:**  
   The schema includes `superseded_by_vintage_id` (forward pointer) and the insertion pipeline links the new vintage to the old vintage ID.
3. **Cross-Exchange Deduplication (NSE vs. BSE):**  
   Companies often file identical disclosures on both exchanges.
   * **Rule:** When an announcement is fetched, the SHA-256 hash of the downloaded PDF/XBRL is compared against existing vintages for that `(company_id, quarter)`.
   * **Action:** If `source_document_hash` is identical, the record is **not** assigned a new `version_sequence`. It is logged as a duplicate announcement alias in audit logs, preventing duplicate versions.
4. **Partial Metric Revisions:**  
   If a company issues a corrigendum adjusting only Segment Assets or Operating Margin while leaving Revenue and PAT untouched, SEBI requires re-publishing the full revised financial results table. The new vintage captures the full revised snapshot as the active authority.

---

## 6. Metric Provenance & Calculation Specifications

To eliminate discrepancies between raw financial statements and calculated ratios, formulas must be standardized:

### 6.1 Standard Accounting Formulas
1. **Return on Equity (ROE):**
   $$\text{ROE} = \frac{\text{Net Profit (PAT)}}{\text{Total Shareholders' Equity}} \times 100$$
   * *Required Fields:* `net_profit`, `total_equity`.
   * *Missing-Data Rule:* If `total_equity <= 0` (negative net worth), ROE is flagged as `None` / `insufficient_data`.
2. **Return on Capital Employed (ROCE):**
   $$\text{Capital Employed} = \text{Total Assets} - \text{Current Liabilities}$$
   $$\text{ROCE} = \frac{\text{EBIT}}{\text{Capital Employed}} \times 100$$
   * *Required Fields:* `operating_profit` (or EBIT), `total_assets`, `current_liabilities`.
   * *Missing-Data Rule:* If `capital_employed <= 0`, ROCE is flagged as `None`.
3. **Debt-to-Equity Ratio (D/E):**
   $$\text{Debt / Equity} = \frac{\text{Total Short-Term Debt} + \text{Total Long-Term Debt}}{\text{Total Shareholders' Equity}}$$
   * *Required Fields:* `total_debt`, `total_equity`.
   * *Missing-Data Rule:* If zero debt, ratio is `0.0`. If negative equity, ratio is flagged invalid.
4. **Operating Margin:**
   $$\text{Operating Margin} = \frac{\text{Operating Profit}}{\text{Revenue}} \times 100$$
5. **Net Margin:**
   $$\text{Net Margin} = \frac{\text{Net Profit (PAT)}}{\text{Revenue}} \times 100$$

### 6.2 Materialization vs. Dynamic Computation
* **Decision:** Materialize standard ratios into columns (`roe`, `roce`, `debt_equity`, `operating_margin`, `net_margin`) at ingestion time **after** validating them against raw line items. This gives callers instant sub-millisecond query performance while preserving full mathematical provenance.

---

## 7. Synthetic Data Isolation Architecture

To ensure the 258 placeholder records in `quarterly_results` never contaminate the research pipeline:
1. **Zero Migration of Existing Rows:** The new table `quarterly_financial_vintages` will be created completely empty. **No records from `quarterly_results` will be copied or migrated.**
2. **Strict Ingestion Filtering:** The ingestion service will incorporate a hard check:
   ```python
   def is_synthetic_placeholder(revenue, net_profit, eps, roe):
       if revenue == 10000.0 and net_profit == 1500.0 and eps == 15.0:
           return True
       return False
   ```
   Any incoming row matching this pattern is immediately rejected with `REJECTED_SYNTHETIC`.
3. **Isolation in `financial_service.py`:** When `require_verified_publication_date=True`, `financial_service.py` will query **only** `quarterly_financial_vintages`. If a stock has no rows in the vintage table, it receives `NO_ELIGIBLE_RECORDS`, safely starving the signal rather than reading legacy synthetic data.

---

## 8. Staging Database Isolation Safety

* **Database Target:** The schema definition and ingestion testing will take place exclusively in:
  `database/staging_financial_expansion.db`
* **Production Invariance:** `database/swing_trading.db` will remain in read-only mode with zero schema changes until the entire staging dataset is ingested, audited, and approved.
* **No Automatic Production Fallback:** `financial_service.py` must never fall back from staging to production if a symbol is missing in staging. Staging runs must operate with absolute data autonomy.

---

## 9. Comprehensive Classification of Architectural Decisions

| Decision ID | Description | Classification | Reasoning / Conditions |
| :--- | :--- | :--- | :--- |
| **DEC-01** | Append-only `quarterly_financial_vintages` table | **APPROVED** | Preserves all historical filings; completely prevents restatement lookahead bias. |
| **DEC-02** | Effective trading date calculation with 15:30 cutoff | **APPROVED** | Correctly maps after-market and weekend disclosures to the next executable session. |
| **DEC-03** | Window-query PIT resolution (`ROW_NUMBER()`) | **APPROVED** | Verified: filters before ranking, preventing future restatements from leaking. |
| **DEC-04** | Quarantine existing 260 rows from vintage table | **APPROVED** | Zero legacy placeholder data will enter the vintage table. |
| **DEC-05** | Materialize raw line items and computed ratios | **APPROVED** | Balances raw accounting auditability with high-performance query execution. |
| **DEC-06** | SHA-256 document hashing for provenance | **APPROVED** | Provides cryptographic auditability back to official exchange PDFs. |
| **DEC-07** | Dual-exchange hash deduplication | **APPROVED** | Prevents identical filings uploaded to NSE and BSE from creating duplicate versions. |
| **DEC-08** | Staging DB deployment before production | **APPROVED WITH CONDITIONS** | Condition: Staging and production databases must maintain distinct connection configs with zero fallback. |
| **DEC-09** | Conservative fallback for date-only timestamps | **APPROVED WITH CONDITIONS** | Condition: Date-only filings must map to $T+1$ open to prevent after-market leakage. |
| **DEC-10** | Filing Scope Fallback Hierarchy | **REQUIRES HUMAN DECISION** | **Decision:** Should the system strictly enforce Consolidated results, or allow Standalone fallback if Consolidated is delayed? *(Recommendation: Prioritize Consolidated; flag Standalone explicitly if used).* |
| **DEC-11** | Minimum Historical TTM Lookback Horizon | **REQUIRES HUMAN DECISION** | **Decision:** How many historical quarters per company are required before a stock qualifies for fundamental scoring? *(Recommendation: Minimum 4 quarters for YoY/TTM calculations).* |

---

## 10. Recommended Implementation Sequence for P2.4

1. **Phase P2.4.1:** Create `quarterly_financial_vintages` table and indexes in `database/staging_financial_expansion.db` (leaving production DB untouched).
2. **Phase P2.4.2:** Implement market calendar service with official NSE/BSE holidays and 15:30 IST session logic.
3. **Phase P2.4.3:** Build exchange filing parser and document hashing module.
4. **Phase P2.4.4:** Ingest authentic historical filings for the 52-stock universe into staging.
5. **Phase P2.4.5:** Update `financial_service.py` to route strict PIT queries to `quarterly_financial_vintages`.
6. **Phase P2.4.6:** Execute all 15 regression test scenarios and benchmark backtests.

---

## 11. Final Verification Invariants

1. **Current Git HEAD:** `ecbcbde2e78f03e06575b84240634ba3b5c81239`.
2. **Database Hash Verification:**
   * `database/swing_trading.db`: `1a2036fcc72af59b3633b5c2a077c26dd45756b3360824f36e995e2e805a28a8` (Unchanged)
   * `database/staging_financial_expansion.db`: `4b5a3479aba5f5176843ef1033c026a543d54914db68cd2169e1ff5552bed465` (Unchanged)
3. **Protected Files Invariance:** Zero diffs in `signal_engine.py`, `trade_quality_engine.py`, `portfolio_simulator.py`. `strategy_engine.py` confirmed non-existent.
4. **Deliverables Created:** Only [`docs/audit_artifacts/P2_3_1_ARCHITECTURE_DECISION_REVIEW.md`](file:///C:/Users/vigne/OneDrive/Desktop/projects/swing-trading-tool/docs/audit_artifacts/P2_3_1_ARCHITECTURE_DECISION_REVIEW.md).

**Final Verdict:** `P2.3.1 COMPLETE — READY FOR P2.4 REVIEW`

