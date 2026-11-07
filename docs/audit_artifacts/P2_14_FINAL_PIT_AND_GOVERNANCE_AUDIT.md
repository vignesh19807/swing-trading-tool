# P2.14 Audit Artifact: Final PIT Session Correction & Financial Data Governance Audit

**Audit Date**: 2026-11-06  
**Auditor**: Principal Financial Data Architect, Senior Python Engineer, Point-in-Time Data Specialist & Independent Financial Data Auditor  
**Target Repository**: `swing-trading-tool`  
**Staging Database**: `database/staging_financial_expansion.db` (28 vintages)  
**Production Database**: `database/swing_trading.db` (Verified Unchanged)  
**Status**: 100% VERIFIED & ENFORCED  

---

## 1. Executive Summary

Phase P2.14 executes the final data governance, session boundary calibration, identifier decoupling, and Point-in-Time (PIT) integrity verification across the P2 roadmap.

The scope of P2 closure is explicitly defined:
- **Conditional Closure for Four Companies**: Tata Consultancy Services (`TCS`), Infosys Limited (`INFY`), Reliance Industries Limited (`RELIANCE`), and Adani Enterprises Limited (`ADANIENT`) have achieved complete authentic source verification against primary exchange PDF disclosures with 100% cryptographic SHA-256 validation.
- **HDFCBANK Quarantined Pilot Exception**: HDFC Bank Limited (`HDFCBANK`) remains an explicit, quarantined pilot exception due to the absence of host optical character recognition (OCR) and PDF rasterization software required to decode its scanned raster image disclosures. Under strict anti-hallucination rules, unverified numbers are not promoted.

---

## 2. Task A: NSE Market Session Correction

### Prior Defect & Mischaracterization
Earlier P2 documentation informally described continuous trading as `09:00 - 15:30 IST`. For National Stock Exchange of India (NSE) equities, this conflated the pre-open auction session with normal continuous trading.

### Calibrated NSE Session Model (Asia/Kolkata)
The exchange trading day is partitioned into five distinct operational phases:

| Session Phase | Window (IST) | Market Characteristics | Actionable Window | Effective Trading Date |
| :--- | :---: | :--- | :--- | :---: |
| **PRE_MARKET** | `< 09:00:00` | Off-hours; no order placement or price discovery. | Known prior to market open. Regular trading begins at 09:15:00. | Same Day (`pub_date`) |
| **PRE_OPEN** | `09:00:00 - 09:14:59` | Order accumulation (09:00–09:08), order matching / equilibrium price discovery (09:08–09:12), transition buffer (09:12–09:15). Normal continuous trading is not open. | Information available prior to continuous market opening at 09:15:00. Actionable during today's regular session. | Same Day (`pub_date`) |
| **CONTINUOUS_TRADING** | `09:15:00 - 15:29:59` | Regular continuous matching session. | Information received during continuous hours can be traded prior to close or in closing auction (15:00–15:30). | Same Day (`pub_date`) |
| **POST_MARKET** | `>= 15:30:00` | Closing price auction/calculation (15:30–15:40) and post-close session (15:40–16:00). Normal continuous trading is closed. | Cannot execute regular trades today. Actionable in next regular session. | Next Trading Day (`get_next_market_trading_day`) |
| **WEEKEND / HOLIDAY** | Full Day | Saturday, Sunday, or official NSE holiday. No trading session. | Actionable in next regular session. | Next Trading Day (`get_next_market_trading_day`) |

### Publication & Processing Delay Policy
- For daily-bar swing trading, orders execute either at the session close (15:20–15:30) or next day open (09:15).
- Continuous trading cutoff is enforced at **`15:30:00 IST`**. Any announcement received strictly prior to 15:30:00 IST (e.g. `15:29:00`) is effective same day (`pub_date`). Any announcement received at or after 15:30:00 IST (e.g. `15:30:00`, `15:31:00`) rolls to the next active trading day.
- Announcements without timestamps or with date-only formats (`YYYY-MM-DD`) conservatively roll forward to the next active trading day to prevent look-ahead bias.

---

## 3. Task B: Timezone & Timestamp Integrity Audit

All 28 staging vintages were audited across all five canonical timestamp columns:

```sql
SELECT id, company_id, quarter, version_sequence, published_at, effective_trading_date, ingested_at, internally_corrected_at, company_revision_published_at
FROM quarterly_financial_vintages;
```

### Key Findings
1. **Exchange Timestamps (`published_at`)**:
   - Preserved as exact exchange-local time strings (`YYYY-MM-DD HH:MM:SS`), representing `Asia/Kolkata` time.
   - For Vintage 28 (`ADANIENT` Q2 FY25), `published_at = '2024-10-29 14:58:48'` exactly preserves the authentic exchange publication timestamp and has not been overwritten by an internal timestamp.
2. **Internal Correction Timestamps (`internally_corrected_at`)**:
   - Stored in UTC (e.g. `'2026-11-06 08:44:21'`), completely decoupled from the exchange publication time.
3. **Effective Trading Date (`effective_trading_date`)**:
   - For Vintage 28, `effective_trading_date = '2024-10-29'` because the announcement was published during continuous trading (14:58:48 IST < 15:30:00 IST).
4. **Timezone Conversion Engine**:
   - `parse_exchange_timestamp()` in `historical_pit_service.py` natively supports naive strings (assumed `Asia/Kolkata`), explicit `'IST'` suffixes, and ISO 8601 UTC/offset strings (converting to `Asia/Kolkata` local time).

---

## 4. Task C: Exchange Identifier & Internal Correction ID Decoupling

### Analysis of Prior Design Limitation
In Phase P2.13, Vintage 28 was inserted with:
`exchange_broadcast_id = 'NSE_ADANIENT_166300_CORRECTED'`
This was internally constructed because the table carried a unique constraint:
`UNIQUE(exchange, exchange_broadcast_id)`
An external auditor could mistake this for an official exchange identifier. In reality:
- The National Stock Exchange of India never emitted a broadcast called `NSE_ADANIENT_166300_CORRECTED`.
- The genuine exchange announcement ID was **`166300`** (canonical `NSE_166300`).
- The correction was an internal pipeline fix (`EXTRACTION_CORRECTION`).

### Architectural Resolution
We have structurally decoupled the four concepts:

| Concept | Definition | Storage in Database | Vintage 25 Value | Vintage 28 Value |
| :--- | :--- | :--- | :--- | :--- |
| **Genuine Exchange Announcement ID** | Canonical identifier assigned by the stock exchange | `original_broadcast_id` | `NSE_166300` | `NSE_166300` |
| **Internal Correction Event ID** | Engineering tracking ID for internal pipeline revisions | `internal_correction_event_id` | `NULL` | `INT_CORR_20261106_ADANIENT_166300_V4` |
| **Original Source Document Hash** | SHA-256 hash of authentic binary PDF | `source_document_hash` | `534e42a8e5da...` | `534e42a8e5da...` |
| **Internal Revision Lineage** | Explicit parent, supersession, and version ordering | `parent_vintage_id`, `supersedes_vintage_id`, `version_sequence` | Parent: 14, Supersedes: 14, Version: 3 | Parent: 25, Supersedes: 25, Version: 4 |

---

## 5. Task D: Revalidation of the Eight Verified Vintages

The eight `VERIFIED_ELIGIBLE` vintages were independently audited against authentic PDF binary files on disk:

| Vintage ID | Issuer | Quarter | Scope | Exchange Seq ID | Verified SHA-256 Fingerprint | Reported Revenue (₹ Cr) | Reported Net Profit (₹ Cr) | Reported EPS | Primary Statement Table Verification |
| :---: | :--- | :---: | :---: | :---: | :--- | :---: | :---: | :---: | :--- |
| **18** | TCS | 2024-Q1 | CONSOLIDATED | `163468` | `dc564e8be40a...` | 62,613.00 | 12,040.00 | 33.28 | Confirmed in Statement of Consolidated Financial Results |
| **19** | TCS | 2024-Q2 | CONSOLIDATED | `165628` | `fd59a27f69aa...` | 64,259.00 | 11,909.00 | 32.90 | Confirmed in Statement of Consolidated Financial Results |
| **20** | INFY | 2024-Q1 | CONSOLIDATED | `163553` | `38afc5e2eac4...` | 39,315.00 | 6,368.00 | 15.35 | Confirmed in Consolidated Statement of Profit and Loss |
| **21** | INFY | 2024-Q2 | CONSOLIDATED | `165698` | `f70b679051e3...` | 40,986.00 | 6,506.00 | 15.68 | Confirmed in Consolidated Statement of Profit and Loss |
| **22** | RELIANCE | 2024-Q1 | CONSOLIDATED | `163612` | `d566e07bebc9...` | 231,784.00 | 15,138.00 | 22.39 | Confirmed in Value of Sales & Services / Profit for the Period |
| **23** | RELIANCE | 2024-Q2 | CONSOLIDATED | `165657` | `fbe90e101b1a...` | 236,217.00 | 17,445.00 | 24.38 | Confirmed in Value of Sales & Services / Profit for the Period |
| **24** | ADANIENT | 2024-Q1 | CONSOLIDATED | `164109` | `c7ca3e1e2db5...` | 25,472.40 | 1,774.25 | 15.56 | Confirmed in Unaudited Consolidated Financial Results Line 1(a) |
| **28** | ADANIENT | 2024-Q2 | CONSOLIDATED | `166300` | `534e42a8e5da...` | **22,608.07** | **1,741.75** | **14.82** | Confirmed in Unaudited Consolidated Financial Results Line 1(a) |

---

## 6. Task E: HDFC Bank Quarantine Policy

HDFC Bank Limited (`HDFCBANK`) remains an explicitly documented pilot exception:
- **Vintages 26 and 27**: Retained in `research_eligibility = 'QUARANTINED'` and `verification_status = 'PROVISIONAL'`.
- **Vintages 7, 8, 15, 16**: Retained in `research_eligibility = 'SUPERSEDED'`.
- **Vintage 17**: Retained in `research_eligibility = 'PROVISIONAL_DEMO'` (standalone banking pilot).
- **Point-in-Time Fail-Closed**: `PointInTimeEligibilityService.get_eligible_vintage_as_of("HDFCBANK", ...)` returns `None` on all historical dates.
- **Future Unlocking Prerequisites**: Requires host installation of Tesseract OCR with English trained data, Poppler / PyMuPDF rasterizer, and a dual-pass OCR extraction protocol with >95% confidence.

---

## 7. Task F & H: Test Suite Execution Results

All 62 tests across the five P2 test modules were executed on isolated temporary SQLite database fixtures:

```
backend/tests/test_p2_14_pit_governance.py ...............               [ 24%]
backend/tests/test_p2_7_to_p2_11.py ....................                 [ 56%]
backend/tests/test_p2_6_schema_lineage.py ...........                    [ 74%]
backend/tests/test_p2_staging_financial_vintage.py ..........            [ 90%]
backend/tests/test_p2_financial_ingestion_pilot.py ......                [100%]

============================= 62 passed in 3.85s ==============================
```

Broader backend verification:
- `backend/tests/test_api_contract.py` & `backend/tests/test_audit_001_financial_lookahead.py`: 22 passed in 14.21s.

---

## 8. Safety & Immutability Verification

1. **Production Database (`database/swing_trading.db`)**:
   - SHA-256: `1a2036fcc72af59b3633b5c2a077c26dd45756b3360824f36e995e2e805a28a8` (100% UNTOUCHED).
   - Rows: 260 quarterly results rows (100% UNTOUCHED).
2. **Protected Files**:
   - `backend/logic/strategy_engine.py` — UNTOUCHED
   - `backend/logic/signal_engine.py` — UNTOUCHED
   - `backend/logic/trade_quality_engine.py` — UNTOUCHED
   - `backend/logic/portfolio_simulator.py` — UNTOUCHED
3. **Git Working Tree**:
   - Zero commits, zero pushes, zero resets.

