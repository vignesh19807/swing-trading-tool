# P2.5.4 — Financial Data Integrity Remediation Design and Source Authenticity Plan

## Executive Summary

| Architectural Item | Current Audit State (P2.5.3) | Target Architecture Design (P2.5.4) |
| :--- | :--- | :--- |
| **Filing Event Classification** | Conflated in `filing_type = 'RESTATED'` | Decoupled 4D Classification (`company_filing_type`, `internal_revision_type`, `verification_status`, `research_eligibility`) |
| **Historical Lineage & Timestamps** | Single announcement timestamp reused across internal fixes | 5-Timestamp Lineage Model separating exchange broadcast, ingestion, internal fixes, and effective trading sessions |
| **Banking Sector Representation** | Corporate D/E (~6.3x) applied; Standalone metrics copied to Consolidated | Dedicated banking schema; D/E nullified; NII/CAR/NPA scope-isolated; customer deposits distinguished from corporate debt |
| **Exchange Source Document Pipeline** | 10 mock ASCII text files (~120 B) stored as test fixtures | Reliable, session-managed NSE/BSE binary pipeline; magic-byte `%PDF-` validation; structure & content audit; SHA-256 fingerprinting |
| **Point-in-Time (PIT) Governance** | Window ranking filters on `effective_trading_date <= eval_date` | Multi-tier eligibility gate preventing unverified or lookahead data from entering live signals or quantitative backtests |
| **17-Vintage Pilot Status** | 10 original pilot + 7 remediation vintages with integrity issues | Formal migration mapping: 6 Superseded, 2 Quarantined, 9 Provisional Demo (zero live promotion without authentic binary source) |
| **Final Milestone Verdict** | — | **`P2.5.4 COMPLETE — HUMAN DECISIONS REQUIRED`** |

---

## 1. P2.5.3 Audit Findings Recap

The independent lineage and integrity audit conducted in `P2.5.3` identified five fundamental data architecture defects across the 17 records in `quarterly_financial_vintages`:

1. **Semantic Conflation of Corporate Events and Pipeline Fixes:** Vintages 11–16 were categorized with `filing_type = 'RESTATED'`. In reality, Reliance Industries, Adani Enterprises, and HDFC Bank filed standard `ORIGINAL` disclosures with NSE/BSE under Regulation 33 of SEBI LODR. The restatements were internal parser and normalization bug-fixes made by our engineering pipeline, not corporate restatement events announced by the companies.
2. **HDFC Bank Scope Mismatch & Metric Contamination:**
   - **Q1 FY25 (Vintage 15):** Top-line revenue remains Standalone Total Income (`₹83,701.25 Cr`), while profit is Consolidated PAT (`₹16,474.85 Cr`). Consolidated Total Income was approximately `₹118,500 Cr`.
   - **Q2 FY25 (Vintage 16):** Standalone Net Interest Income (`₹30,111 Cr`), Standalone Capital Adequacy (`19.80%`), and Standalone NPAs (`1.36% / 0.41%`) were copied directly into Consolidated scope.
   - **Legacy Pilot (Vintages 7 & 8):** Treated customer deposits as conventional corporate debt, producing misleading $D/E$ ratios of `6.36x` and `6.26x`.
3. **Absence of Authentic Binary Source Documents:** All 10 stored `.pdf` files in `database/staging_filings_store/` are 113–135 byte single-line ASCII test strings. The SHA-256 hashes recorded in the database hash these test strings, not official signed exchange disclosure documents.
4. **Point-in-Time Visibility Risks:** Internal corrections shared the original exchange publication timestamp without tracking pipeline modification dates, creating a structural risk where future corporate restatements could inherit historical publication dates.
5. **Research Governance Gap:** The system lacked an explicit research eligibility gate, allowing any record with `verification_status = 'VERIFIED'` to be consumed by scoring algorithms, even when source documents were mock fixtures.

---

## 2. Task A — Four-Dimensional Data Classification Schema

To prevent semantic conflation, the financial data layer must decouple corporate disclosure types, data engineering lifecycles, audit verification states, and algorithmic research eligibility into four independent dimensions.

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                        FOUR-DIMENSIONAL DATA CLASSIFICATION                            │
└────────────────────────────────────────────────────────────────────────────────────────┘
         │                                                      │
         ▼                                                      ▼
┌─────────────────────────────────┐                    ┌─────────────────────────────────┐
│     1. COMPANY FILING TYPE      │                    │   2. INTERNAL REVISION TYPE     │
│   (Official Exchange Action)    │                    │ (Data Pipeline Lifecycle Stage) │
├─────────────────────────────────┤                    ├─────────────────────────────────┤
│ • ORIGINAL                      │                    │ • INITIAL_INGESTION             │
│ • REVISED_DISCLOSURE            │                    │ • EXTRACTION_CORRECTION         │
│ • CORPORATE_RESTATEMENT         │                    │ • SCOPE_REALIGNMENT             │
│ • ANNUAL_AUDITED_FINAL          │                    │ • SECTOR_NORMALIZATION          │
└─────────────────────────────────┘                    └─────────────────────────────────┘
         │                                                      │
         ▼                                                      ▼
┌─────────────────────────────────┐                    ┌─────────────────────────────────┐
│     3. VERIFICATION STATUS      │                    │    4. RESEARCH ELIGIBILITY      │
│   (Audit Evidence Integrity)    │                    │ (Trading & Scoring Permissions) │
├─────────────────────────────────┤                    ├─────────────────────────────────┤
│ • VERIFIED                      │                    │ • VERIFIED_ELIGIBLE             │
│ • PROVISIONAL                   │                    │ • PROVISIONAL_DEMO              │
│ • REJECTED                      │                    │ • QUARANTINED                   │
│                                 │                    │ • SUPERSEDED                    │
└─────────────────────────────────┘                    └─────────────────────────────────┘
```

### Dimension 1: Company Filing Type (`company_filing_type`)
Represents the official corporate disclosure event broadcasted by the listed company on the stock exchange (NSE/BSE).

| Value | Definition | Mandatory Evidence Requirements |
| :--- | :--- | :--- |
| **`ORIGINAL`** | The primary quarterly or annual financial filing submitted under SEBI LODR Regulation 33. | Unique exchange broadcast ID, official exchange timestamp, board meeting outcome PDF attachment. |
| **`REVISED_DISCLOSURE`** | A revised filing submitted by the company to correct clerical errors, missing schedules, or typographical mistakes in the original disclosure. | Official exchange addendum announcement referencing the original broadcast ID; revised attachment hash. |
| **`CORPORATE_RESTATEMENT`** | A formal retrospective restatement of accounts arising from mergers, demergers, scheme of arrangements, or changes in accounting policy under Ind AS 8. | Detailed restatement reconciliation note published in exchange disclosures (e.g., Draft Letter of Offer or Scheme filing). |
| **`ANNUAL_AUDITED_FINAL`** | The audited annual financial results or published Annual Report replacing limited quarterly reviews. | Statutory Auditor's Unqualified/Qualified Audit Report with full audited balance sheet and cash flows. |

*Rule:* An internal pipeline bug-fix must **NEVER** be categorized as `REVISED_DISCLOSURE` or `CORPORATE_RESTATEMENT`.

### Dimension 2: Internal Revision Type (`internal_revision_type`)
Represents the technical lifecycle event within our ingestion and data normalization pipeline.

| Value | Definition | Traceability / Linkage Requirements |
| :--- | :--- | :--- |
| **`INITIAL_INGESTION`** | The first automated ingestion of a company filing. | Initial vintage sequence (`version_sequence = 1`); `superseded_by_vintage_id = NULL`. |
| **`EXTRACTION_CORRECTION`** | Re-extraction of line items to fix parser, OCR, regex, or unit errors (e.g., Reliance net vs. gross turnover). | Increments `version_sequence`; sets `superseded_by_vintage_id` on predecessor; records correction note and auditor ID. |
| **`SCOPE_REALIGNMENT`** | Correction of reporting scope boundaries (e.g., separating Standalone from Consolidated statements). | Links to previous mismatched vintage; preserves original publication date; mandates separate Standalone and Consolidated rows. |
| **`SECTOR_NORMALIZATION`** | Schema-level adjustment for industry-specific metrics (e.g., nullifying bank D/E, mapping Net Interest Income). | Cross-references parent vintage; applies sector schema rules; nullifies inapplicable general corporate ratios. |

### Dimension 3: Verification Status (`verification_status`)
Represents the level of audit certainty established for the stored financial data against authentic primary documents.

| Value | Definition | Objective Criteria |
| :--- | :--- | :--- |
| **`VERIFIED`** | All reported figures match an authentic, multi-page binary exchange disclosure document. | Genuine binary PDF preserved locally; magic-byte validation passed; SHA-256 fingerprint verified; line items reconciled against auditor's report. |
| **`PROVISIONAL`** | Reported figures are consistent with exchange broadcast text or multiple secondary sources, but authentic binary document is pending. | Source URL verified; broadcast text matches; binary PDF is pending session retrieval or automated retry (`SOURCE_DOCUMENT_UNAVAILABLE`). |
| **`REJECTED`** | Figures fail accounting validation, show severe balance-sheet discrepancies, or lack provenance. | Mathematical mismatch ($Assets \ne Liabilities + Equity$); negative revenue; unit conversion failure; duplicate broadcast ID. |

### Dimension 4: Research Eligibility (`research_eligibility`)
Enforces algorithmic permissioning across system consumers, preventing unverified or contaminated data from reaching execution engines.

| Value | Allowed Consumers | Blocked Consumers | Promotion Criteria |
| :--- | :--- | :--- | :--- |
| **`VERIFIED_ELIGIBLE`** | Live Trading Signals, Backtesting Engine, Opportunity Scoring, Web APIs. | None. | Requires `verification_status = 'VERIFIED'` and authentic binary document preserved. |
| **`PROVISIONAL_DEMO`** | UI Visualizations, Sandbox Analysis, Staging Diagnostic Tools. | **BLOCKED:** Live Trading, Strategy Backtesting, Signal Engine. | Basic numerical consistency verified; binary PDF pending. |
| **`QUARANTINED`** | Data Engineering Audit, Lineage Inspection Tools. | **BLOCKED:** All trading, scoring, backtesting, and production APIs. | Detected scope contamination, unverified corporate restatement, or unresolved anomaly. |
| **`SUPERSEDED`** | Historical Audit Trail, Lineage Visualizers. | **BLOCKED:** All active algorithmic decision engines. | Replaced by a higher `version_sequence` vintage. |

---

## 3. Task B — Historical Lineage and Restatement Design

To maintain strict point-in-time invariants, the platform must track five distinct timestamps for every financial vintage:

```
Timeline of Events & Respective Timestamps:

       Company Broadcasts                 Pipeline Ingestion               Pipeline Bug Fix                 Market Session Opens
       Filing to Exchange                    First Run                       (Parser Fix)                  (First Trading Session)
               │                                 │                                 │                                  │
               ▼                                 ▼                                 ▼                                  ▼
      [published_at]                      [ingested_at]              [internally_corrected_at]           [effective_trading_date]
   2024-07-19 18:00:00 IST             2024-07-19 18:15:00 IST           2026-11-04 16:20:00 IST                 2024-07-22
```

### The Five Canonical Timestamps
1. **`published_at` (`exchange_publication_timestamp`):** The exact broadcast timestamp recorded by NSE/BSE when the company's filing became public.
2. **`ingested_at` (`pipeline_ingested_at`):** The system timestamp when our platform first ingested and stored the record.
3. **`internally_corrected_at` (`pipeline_corrected_at`):** The system timestamp when an internal extraction or scope correction was executed.
4. **`effective_trading_date`:** The date of the first market session where participants could execute trades based on the disclosed information (derived deterministically from `published_at`).
5. **`company_revision_published_at`:** If the company filed a revised disclosure or restatement, the exact timestamp of that *new* exchange filing.

### Lineage Progression Rules

#### Case 1: Internal Extraction Correction
- **Context:** An internal regex parsed gross revenue instead of revenue from operations on day one.
- **Rule:** The corrected record fixes our reading of what was *already publicly available* on `published_at`.
- **Implementation:**
  - Create a new vintage with incremented `version_sequence` ($v2$).
  - `company_filing_type` remains `ORIGINAL`.
  - `internal_revision_type = 'EXTRACTION_CORRECTION'`.
  - `published_at` and `effective_trading_date` **must remain identical** to the original disclosure.
  - Set `superseded_by_vintage_id` on $v1$ pointing to $v2$.
  - Record the actual fix time in `internally_corrected_at`.

#### Case 2: Company-Announced Revised Disclosure / Restatement
- **Context:** The company issued an addendum or restatement on the exchange two months later.
- **Rule:** This is a *new market event*. Information from this restatement was physically unavailable to the market prior to the new filing date.
- **Implementation:**
  - Create a new vintage ($v2$).
  - `company_filing_type` set to `REVISED_DISCLOSURE` or `CORPORATE_RESTATEMENT`.
  - `published_at` set to the **new** exchange announcement timestamp.
  - `effective_trading_date` computed from the **new** announcement timestamp.
  - The predecessor $v1$ remains active for historical evaluations prior to the restatement's effective date!

```
Historical Point-in-Time Query Evaluation:

Evaluation Date T < Restatement Date:
┌────────────────────────────────────────────────────────┐
│ PIT Query retrieves Vintage v1 (Original Filing)       │  <-- No Lookahead Leakage!
└────────────────────────────────────────────────────────┘

Evaluation Date T >= Restatement Date:
┌────────────────────────────────────────────────────────┐
│ PIT Query retrieves Vintage v2 (Restated Filing)       │  <-- Reflects Updated Reality!
└────────────────────────────────────────────────────────┘
```

---

## 4. Task C — HDFC Bank Metric Scope Remediation Design

Commercial banks operate under fundamentally different accounting and economic models compared to industrial companies. Applying non-financial balance sheet models creates severe distortions.

### Fundamental Banking Principles
1. **Customer Deposits are Operational Liabilities, Not Debt:** Customer deposits are the primary raw material of a commercial bank. Treating deposits as corporate borrowings produces astronomical and meaningless Debt-to-Equity ratios ($>6.0x$). In banking, corporate solvency is measured via **Capital Adequacy Ratio (CAR / CRAR)** under RBI Basel III guidelines.
2. **Revenue is Net Interest Income + Other Income:** Top-line revenue in commercial banking is driven by interest earned less interest expended (NII).
3. **Asset Quality is Governed by NPA Provisions:** Credit health is evaluated via Gross NPA %, Net NPA %, and Provision Coverage Ratio (PCR), not current liabilities or debt coverage ratios.

### Remediation of Identified HDFC Bank Defects

```
                                  HDFC BANK SCOPE REMEDIATION
                                 
      [CONSOLIDATED DISCLOSURE]                                   [STANDALONE DISCLOSURE]
┌────────────────────────────────────┐                      ┌────────────────────────────────────┐
│ • Total Income: ₹121,457 Cr (Q2)   │                      │ • Total Income: ₹85,499.64 Cr (Q2) │
│ • Net Profit:   ₹17,830 Cr (Q2)    │                      │ • Net Profit:   ₹16,821 Cr (Q2)    │
│ • Net Interest Income: NULL *      │                      │ • Net Interest Income: ₹30,111 Cr  │
│ • Capital Adequacy:    19.30% *    │                      │ • Capital Adequacy:    19.80%      │
│ • Gross NPA %:         NULL *      │                      │ • Gross NPA %:         1.36%       │
│ • Net NPA %:           NULL *      │                      │ • Net NPA %:           0.41%       │
│ • Customer Deposits:   NULL *      │                      │ • Customer Deposits:   ₹25,00,100Cr│
└────────────────────────────────────┘                      └────────────────────────────────────┘
  * Explicitly NULL: Standalone metrics                       Parent bank specific statutory
    prohibited from polluting Consolidated                     disclosures regulated by RBI.
```

1. **Resolution of Vintage 15 (Q1 FY25 Consolidated Scope Mismatch):**
   - **Current State:** Staged with `revenue = ₹83,701.25 Cr` (Standalone Total Income) while `net_profit = ₹16,474.85 Cr` (Consolidated PAT).
   - **Remediation:** Quarantine Vintage 15 immediately (`research_eligibility = 'QUARANTINED'`). Insert a new aligned vintage once authentic Consolidated Total Income (`~₹118,500 Cr`) is extracted from the official filing.
2. **Resolution of Vintage 16 (Q2 FY25 Consolidated Metric Copying):**
   - **Current State:** Copied Standalone NII (`₹30,111 Cr`), Standalone CAR (`19.80%`), and Standalone NPAs (`1.36% / 0.41%`) into Consolidated scope.
   - **Remediation:** Set `net_interest_income = NULL`, `capital_adequacy_ratio = 19.30%` (Consolidated CRAR per filing), `gross_npa_pct = NULL`, `net_npa_pct = NULL`, and `customer_deposits = NULL` on the Consolidated record.
3. **Resolution of Vintage 17 (Q2 FY25 Standalone Scope):**
   - Retain Standalone figures (`revenue = 85499.64`, `net_profit = 16821.0`, `nii = 30111.0`, `car = 19.80%`, `gnpa = 1.36%`, `nnpa = 0.41%`, `deposits = 2500100.0`).
   - Categorize as `PROVISIONAL_DEMO` pending authentic binary PDF retrieval.
4. **Resolution of Vintages 7 & 8 (Legacy Debt/Equity Invariant):**
   - In all banking records, `debt_equity` and `roce` must be set to `NULL`. The database schema must enforce `CHECK(is_banking_institution = 0 OR debt_equity IS NULL)`.

---

## 5. Task D — Authentic NSE/BSE Source Document Pipeline

To transition from synthetic test fixtures to authentic exchange filings, an automated, robust, and policy-compliant document retrieval architecture is required.

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                 AUTHENTIC EXCHANGE SOURCE RETRIEVAL ARCHITECTURE                       │
└────────────────────────────────────────────────────────────────────────────────────────┘
                                           │
                                           ▼
                      ┌─────────────────────────────────────────┐
                      │ 1. Exchange Announcement Discovery      │
                      │    (NSE / BSE Corporate Filings API)    │
                      └─────────────────────────────────────────┘
                                           │
                                           ▼
                      ┌─────────────────────────────────────────┐
                      │ 2. Security & Filing Period Mapping     │
                      │    (Symbol -> ISIN -> Quarter Match)    │
                      └─────────────────────────────────────────┘
                                           │
                                           ▼
                      ┌─────────────────────────────────────────┐
                      │ 3. Session-Managed Attachment Download  │
                      │    (Session Handshake, Rate Limiting)   │
                      └─────────────────────────────────────────┘
                                           │
                                           ▼
                      ┌─────────────────────────────────────────┐
                      │ 4. Multi-Layer PDF Integrity Validation │
                      │    • Magic Bytes: %PDF-                 │
                      │    • Minimum Size: > 50 KB              │
                      │    • Structural Audit: %%EOF & Catalog  │
                      │    • Text Audit: CIN / Auditor Report   │
                      └─────────────────────────────────────────┘
                                           │
                    ┌──────────────────────┴──────────────────────┐
                    │                                             │
             [Passed Audit]                                [Failed Audit]
                    │                                             │
                    ▼                                             ▼
┌──────────────────────────────────────┐      ┌──────────────────────────────────────┐
│ 5. SHA-256 Fingerprinting & Storage  │      │ 6. Failure Logging & Fallback Queue  │
│    database/staging_filings_store/   │      │    Status: SOURCE_UNAVAILABLE        │
│    Status: VERIFIED                  │      │    Eligibility: PROVISIONAL_DEMO     │
└──────────────────────────────────────┘      └──────────────────────────────────────┘
```

### 15 Core Architectural Requirements
1. **Exchange Announcement Discovery:** Query official NSE corporate announcement endpoints (`https://www.nseindia.com/api/corporate-announcements?index=equities`) and BSE corporate announcement endpoints filtering on Category = `Financial Results`.
2. **Security Mapping:** Resolve NSE Symbol (`RELIANCE`), BSE Scrip Code (`500325`), and ISIN (`INE002A01018`) via an immutable security master table.
3. **Filing Period Identification:** Extract reporting quarter and financial period end date using strict date-boundary regex matching against announcement subject headers.
4. **Original Announcement Timestamp:** Parse exact exchange broadcast timestamp in `Asia/Kolkata` timezone with millisecond preservation where available.
5. **Attachment URL Resolution:** Resolve relative attachment paths to fully-qualified archive URLs (`https://nsearchives.nseindia.com/corporate/...` or `https://www.bseindia.com/xml-data/corpfiling/AttachLive/...`).
6. **Binary Stream Retrieval:** Download binary stream directly using session-managed streaming HTTP clients (`httpx` or `requests.Session`).
7. **PDF Magic-Byte Validation:** Verify that the first 5 bytes match `b'%PDF-'`. Reject any response returning HTML error pages, XML gateway errors, or plain text.
8. **File Size & Content Validation:** Genuine financial filings contain multi-page balance sheets, limited review reports, and notes. Enforce a minimum file size threshold of **50 KB**. Reject files $<50\text{ KB}$ as placeholder artifacts.
9. **Structural PDF Integrity:** Parse document structure using a native PDF parser (`pdfplumber` / `pypdf`) to verify valid cross-reference tables (`xref`), catalog dictionaries, and terminal EOF marker (`%%EOF`).
10. **Document Content Verification:** Extract first-page text to verify the presence of listed entity metadata: corporate identification number (CIN), SEBI Regulation 33 disclosure headers, or Statutory Auditor review signatures.
11. **Cryptographic SHA-256 Fingerprinting:** Compute the hexadecimal SHA-256 digest directly from the raw binary stream.
12. **Content-Addressable Storage:** Store binary files under a deterministic, content-addressable filesystem layout:
    `database/staging_filings_store/<EXCHANGE>/<SYMBOL>/<YEAR>/<SHA256[:16]>_<FILENAME>.pdf`.
13. **Duplicate Detection:** Deduplicate filings by matching SHA-256 hashes against existing preserved documents to prevent redundant downloads.
14. **Exchange Rate Limiting & Session Management:**
    - Perform initial handshake against exchange homepages to acquire legitimate session tokens and cookies.
    - Enforce a strict rate limit of $\le 1\text{ request / 2 seconds}$ with exponential backoff on HTTP 429.
    - **Zero-Bypass Policy:** Never bypass access controls, spoof authentication, or circumvent anti-bot challenges. If an automated request is gated by Cloudflare/Akamai challenges, record `retrieval_status = 'BOT_GATE_CHALLENGED'` and trigger operator review.
15. **Audit Trail Logging:** Maintain an append-only JSONL retrieval log recording timestamp, HTTP status, bytes received, and SHA-256 digest for every download attempt.

---

## 6. Task E — Point-in-Time (PIT) Eligibility Rules

Point-in-time financial research requires deterministic visibility boundaries. A strategy evaluated on historical date $T$ must consume only the information that was physically available and executable at that moment.

### Operational Market Timing Scenarios

| Disclosure Timing | Exchange Published At | Market Session State | Effective Trading Date | Rationale |
| :--- | :--- | :--- | :---: | :--- |
| **Intraday Market Hours** | Thursday 11:30 IST | Continuous Trading | Same Day (`2024-07-11`) | Information executable during the active session. |
| **After Market Hours** | Thursday 17:30 IST | Closed | Next Trading Day (`2024-07-12`) | Published after 15:30 IST; executable next morning. |
| **Pre-Market Hours** | Friday 08:15 IST | Pre-Open Session | Same Day (`2024-07-12`) | Published before 09:00 IST pre-open; executable at open. |
| **Weekend Announcement** | Saturday 12:30 IST | Closed (Weekend) | Next Monday (`2024-07-22`) | Markets closed; executable next trading session. |
| **Trading Holiday** | Aug 15 10:00 IST (Holiday) | Closed (Holiday) | Next Trading Day (`2024-08-16`) | NSE trading holiday; mapped to next calendar session. |
| **Missing Timestamp** | Date known, Time NULL | Unknown | Next Trading Day $+ 1\text{ Day}$ | Conservative buffer applied; flagged as `TIMING_FALLBACK`. |

### Visibility Governance Rules
1. **Internal Corrections Do Not Create Lookahead:** If an internal extraction correction fixes an error against an authentic original filing, the corrected record becomes visible on the original `effective_trading_date`. Market participants had the authentic numbers on that date; our system was merely reading them incorrectly.
2. **Company Restatements Cannot Leak Backward:** A company-announced restatement or amended filing must become visible **only on the effective trading date derived from the restatement announcement timestamp**. It must never be backdated to the original filing date.
3. **Unverified Source Documents Block Live Execution:** Any record whose source document is classified as `TEST_MOCK_ARTIFACT` or `SOURCE_DOCUMENT_UNAVAILABLE` is restricted to `research_eligibility = 'PROVISIONAL_DEMO'`. It is strictly excluded from live signal generation and backtest trade execution.

---

## 7. Task F — Migration Plan for the Existing 17 Vintages

The 17 vintages currently staged in `staging_financial_expansion.db` must be migrated to the proposed four-dimensional schema. No record will be deleted, preserving complete audit lineage.

### Proposed 17-Vintage Migration Matrix

| ID | Symbol | Quarter | Scope | Proposed `company_filing_type` | Proposed `internal_revision_type` | Proposed `verification_status` | Proposed `research_eligibility` | Target Action | Architectural Justification |
| :---: | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **1** | TCS | 2024-Q1 | CONSOLIDATED | `ORIGINAL` | `INITIAL_INGESTION` | `PROVISIONAL` | `PROVISIONAL_DEMO` | Keep | Authentic figures; binary PDF pending retrieval. |
| **2** | TCS | 2024-Q2 | CONSOLIDATED | `ORIGINAL` | `INITIAL_INGESTION` | `PROVISIONAL` | `PROVISIONAL_DEMO` | Keep | Authentic figures; binary PDF pending retrieval. |
| **3** | INFY | 2024-Q1 | CONSOLIDATED | `ORIGINAL` | `INITIAL_INGESTION` | `PROVISIONAL` | `PROVISIONAL_DEMO` | Keep | Authentic figures; binary PDF pending retrieval. |
| **4** | INFY | 2024-Q2 | CONSOLIDATED | `ORIGINAL` | `INITIAL_INGESTION` | `PROVISIONAL` | `PROVISIONAL_DEMO` | Keep | Authentic figures; binary PDF pending retrieval. |
| **5** | RELIANCE | 2024-Q1 | CONSOLIDATED | `ORIGINAL` | `INITIAL_INGESTION` | `REJECTED` | `SUPERSEDED` | Supersede | Replaced by Vintage 11 (gross turnover extracted). |
| **6** | RELIANCE | 2024-Q2 | CONSOLIDATED | `ORIGINAL` | `INITIAL_INGESTION` | `PROVISIONAL` | `SUPERSEDED` | Supersede | Replaced by Vintage 12 (turnover breakdown enriched). |
| **7** | HDFCBANK | 2024-Q1 | CONSOLIDATED | `ORIGINAL` | `INITIAL_INGESTION` | `REJECTED` | `SUPERSEDED` | Supersede | Corporate D/E (6.36x) invalid for banking entity. |
| **8** | HDFCBANK | 2024-Q2 | CONSOLIDATED | `ORIGINAL` | `INITIAL_INGESTION` | `REJECTED` | `SUPERSEDED` | Supersede | Scope mismatch (Standalone revenue with Cons PAT). |
| **9** | ADANIENT | 2024-Q1 | CONSOLIDATED | `ORIGINAL` | `INITIAL_INGESTION` | `REJECTED` | `SUPERSEDED` | Supersede | Total income stored in operating revenue. |
| **10** | ADANIENT | 2024-Q2 | CONSOLIDATED | `ORIGINAL` | `INITIAL_INGESTION` | `PROVISIONAL` | `SUPERSEDED` | Supersede | Replaced by Vintage 14 (total income enriched). |
| **11** | RELIANCE | 2024-Q1 | CONSOLIDATED | `ORIGINAL` | `EXTRACTION_CORRECTION` | `PROVISIONAL` | `PROVISIONAL_DEMO` | Reclassify | Fix `filing_type` from RESTATED to ORIGINAL. |
| **12** | RELIANCE | 2024-Q2 | CONSOLIDATED | `ORIGINAL` | `EXTRACTION_CORRECTION` | `PROVISIONAL` | `PROVISIONAL_DEMO` | Reclassify | Fix `filing_type` from RESTATED to ORIGINAL. |
| **13** | ADANIENT | 2024-Q1 | CONSOLIDATED | `ORIGINAL` | `EXTRACTION_CORRECTION` | `PROVISIONAL` | `PROVISIONAL_DEMO` | Reclassify | Fix `filing_type` from RESTATED to ORIGINAL. |
| **14** | ADANIENT | 2024-Q2 | CONSOLIDATED | `ORIGINAL` | `EXTRACTION_CORRECTION` | `PROVISIONAL` | `PROVISIONAL_DEMO` | Reclassify | Enriched total income metadata. |
| **15** | HDFCBANK | 2024-Q1 | CONSOLIDATED | `ORIGINAL` | `SCOPE_REALIGNMENT` | `REJECTED` | `QUARANTINED` | Quarantine | Revenue retains Standalone figure (₹83,701 Cr). |
| **16** | HDFCBANK | 2024-Q2 | CONSOLIDATED | `ORIGINAL` | `SCOPE_REALIGNMENT` | `REJECTED` | `QUARANTINED` | Quarantine | Standalone NII/NPA copied into Consolidated scope. |
| **17** | HDFCBANK | 2024-Q2 | STANDALONE | `ORIGINAL` | `INITIAL_INGESTION` | `PROVISIONAL` | `PROVISIONAL_DEMO` | Keep | Standalone metrics valid; binary PDF pending. |

---

## 8. Task G — Test Strategy

A rigorous test harness must be implemented to validate all architectural invariants prior to production readiness.

### 1. Classification & Invariant Tests
- `test_internal_correction_never_sets_restated_filing_type`: Verifies that pipeline extraction corrections cannot populate `company_filing_type = 'CORPORATE_RESTATEMENT'`.
- `test_invalid_classification_combinations_rejected`: Asserts database-level rejection if `research_eligibility = 'VERIFIED_ELIGIBLE'` is paired with `verification_status = 'PROVISIONAL'`.
- `test_immutable_history_preservation`: Asserts that updating financial numbers on a `VERIFIED` record raises an abort trigger.

### 2. Historical Lineage & Point-in-Time Tests
- `test_internal_correction_preserves_original_published_at`: Verifies that an extraction correction retains the original exchange publication timestamp.
- `test_company_restatement_receives_independent_effective_date`: Asserts that a genuine corporate restatement published on date $T_2$ is invisible to evaluations evaluated at $T_1 < T_2$.
- `test_session_and_holiday_mapping`: Tests market hours (09:15–15:30 IST), post-market filings, weekend filings, and NSE official trading holidays against the NSE calendar.

### 3. Banking Sector & Scope Isolation Tests
- `test_banking_deposits_excluded_from_debt`: Verifies that customer deposits do not populate `total_debt` and that `debt_equity` is strictly `NULL`.
- `test_standalone_banking_metrics_cannot_pollute_consolidated`: Asserts that querying Consolidated HDFC Bank returns `NULL` for NII and NPAs unless explicitly published as consolidated.
- `test_consolidated_revenue_and_profit_scope_matching`: Validates that top-line and bottom-line items on a consolidated record derive from the same reporting boundary.

### 4. Source Document Authenticity Tests
- `test_mock_ascii_pdf_rejected_as_authentic`: Confirms that files $<50\text{ KB}$ or lacking binary PDF EOF markers are rejected from `VERIFIED` status.
- `test_sha256_binary_stream_verification`: Verifies that `source_document_hash` exactly matches the SHA-256 digest of the downloaded binary file.
- `test_failed_retrieval_produces_provisional_status`: Asserts that network failures or bot-gate challenges gracefully fall back to `PROVISIONAL_DEMO` without crashing ingestion.

---

## 9. Task H — Phased Implementation Roadmap

To maintain complete codebase stability and verify each milestone independently, the remediation is broken into four sequential phases:

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                        PHASED IMPLEMENTATION ROADMAP                                   │
└────────────────────────────────────────────────────────────────────────────────────────┘
                                           │
                                           ▼
┌────────────────────────────────────────────────────────────────────────────────────────┐
│ Phase P2.6: Schema Decoupling & 4D Classification Implementation                       │
│ • Objective: Implement decoupled 4D schema & append-only triggers in staging.          │
│ • Database: staging_financial_expansion.db (Production remains untouched).            │
│ • Deliverable: Migration script, updated service layer, classification unit tests.     │
└────────────────────────────────────────────────────────────────────────────────────────┘
                                           │
                                           ▼
┌────────────────────────────────────────────────────────────────────────────────────────┐
│ Phase P2.7: Authentic Exchange Document Retrieval Engine                               │
│ • Objective: Implement session-managed NSE/BSE downloader & binary validator.           │
│ • Components: Magic-byte validator, content extractor, SHA-256 hasher, retry queue.    │
│ • Deliverable: FilingRetriever module, document integrity tests, PDF fixtures.         │
└────────────────────────────────────────────────────────────────────────────────────────┘
                                           │
                                           ▼
┌────────────────────────────────────────────────────────────────────────────────────────┐
│ Phase P2.8: Banking Sector Model & HDFC Scope Realignment                              │
│ • Objective: Realign HDFC Bank Q1 & Q2 records; isolate Standalone banking metrics.    │
│ • Data: Genuine Consolidated Total Income extracted; Standalone NII/NPA isolated.     │
│ • Deliverable: Scope-safe banking parser, banking test suite, remediated vintages.     │
└────────────────────────────────────────────────────────────────────────────────────────┘
                                           │
                                           ▼
┌────────────────────────────────────────────────────────────────────────────────────────┐
│ Phase P2.9: 17-Vintage Migration & Production Readiness Audit                          │
│ • Objective: Execute 17-vintage migration in staging; run 100% test regression.       │
│ • Verification: Independent audit report, production promotion readiness evaluation.   │
│ • Deliverable: Final audit sign-off, production migration plan.                        │
└────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 10. Risks and Unresolved Questions

1. **Exchange Access Restrictions (NSE / BSE Web Gateways):**
   - *Risk:* NSE archives frequently employ Akamai bot protection. Automated headless downloading may periodically experience HTTP 403 blocks.
   - *Mitigation:* The system must support an official, documented fallback mechanism: operator-assisted manual download queue where an analyst places authentic binary PDFs into an ingestion inbox, followed by automated SHA-256 verification and parsing.
2. **Consolidated Banking Metric Availability:**
   - *Risk:* In Indian banking, certain subsidiaries (e.g., life insurance, asset management) operate under distinct regulatory bodies (IRDAI, SEBI). Group-level Consolidated NPA is not an officially recognized metric under RBI IRAC norms.
   - *Mitigation:* The platform must formally treat credit quality metrics as parent-bank (Standalone) indicators and avoid synthesizing artificial group-level credit ratios.
3. **Historical Backtesting Data Volume:**
   - *Risk:* Relying exclusively on manual PDF verification will limit universe expansion speed.
   - *Mitigation:* The four-tier eligibility architecture safely allows `PROVISIONAL_DEMO` data for developer sandboxes while maintaining strict `VERIFIED_ELIGIBLE` gates for capital backtesting.

---

## 11. Human Approval Decisions Required

The following architectural decisions require explicit human confirmation before Phase P2.6 implementation begins:

1. **Decision DEC-P2.5.4-01: Exchange Document Ingestion Mode**
   - *Option A (Recommended):* Implement a dual-mode document pipeline: automated session-managed HTTP retrieval with an automatic fallback to an operator-assisted drop directory when exchange bot gates are encountered.
   - *Option B:* Strict automated-only retrieval; abort ingestion whenever an automated HTTP request is blocked.
2. **Decision DEC-P2.5.4-02: Banking Sector Solvency Metric in Strategy Engine**
   - *Option A (Recommended):* For commercial banks, dynamically replace Debt-to-Equity ($D/E$) with Capital Adequacy Ratio (CRAR) in the scoring algorithm (scoring $>16\%$ as optimal solvency).
   - *Option B:* Simply omit solvency scoring for commercial banks, leaving the solvency component neutral.
3. **Decision DEC-P2.5.4-03: Scope Hierarchy for Multi-Entity Conglomerates**
   - *Option A (Recommended):* Prioritize Consolidated financial records for operational scoring (Revenue, PAT, Margins), but evaluate Standalone records for banking-specific statutory ratios (NII, NPA, CRAR).
   - *Option B:* Enforce strict Consolidated-only scoring, setting all non-consolidated banking ratios to NULL.

---

## 12. Final Readiness Verdict

```
========================================================================================
FINAL VERDICT: P2.5.4 COMPLETE — HUMAN DECISIONS REQUIRED
========================================================================================
- The data integrity remediation design is technically complete and fully documented.
- Four-dimensional classification schema formally decouples corporate events from pipeline fixes.
- Scope-safe banking model resolves HDFC Bank contamination.
- Reliable exchange document pipeline designed with multi-layer PDF validation.
- All safety invariants respected: Zero mutations to production or staging databases.
- Phase P2.6 implementation must await human review of Decisions DEC-P2.5.4-01 through 03.
========================================================================================
```

---

## 13. Final Verification Audit Trail

| Verification Item | Baseline Measurement | Final Measurement | Status |
| :--- | :--- | :--- | :---: |
| **Production DB Hash** | `1a2036fcc72af59b3633b5c2a077c26dd45756b3360824f36e995e2e805a28a8` | `1a2036fcc72af59b3633b5c2a077c26dd45756b3360824f36e995e2e805a28a8` | **IDENTICAL** |
| **Staging DB Hash** | `6ea5a58bce4accd276255794b8e2001c68adeedb79daf2804d1d16a94f698e7b` | `6ea5a58bce4accd276255794b8e2001c68adeedb79daf2804d1d16a94f698e7b` | **IDENTICAL** |
| **Production Row Count** | 260 rows (`quarterly_results`) | 260 rows (`quarterly_results`) | **IDENTICAL** |
| **Staging Row Count** | 17 rows (`quarterly_financial_vintages`) | 17 rows (`quarterly_financial_vintages`) | **IDENTICAL** |
| **Protected Engine Files** | `strategy_engine.py`, `signal_engine.py`, `trade_quality_engine.py`, `portfolio_simulator.py` | 0 modifications | **UNTOUCHED** |
| **Git Working Tree** | `ecbcbde2e78f03e06575b84240634ba3b5c81239` (0 diffs against HEAD) | 0 diffs against HEAD | **CLEAN** |
| **Artifact Created** | None | `docs/audit_artifacts/P2_5_4_FINANCIAL_INTEGRITY_REMEDIATION_DESIGN.md` | **1 FILE** |

