# P2.5.3 — Financial Remediation Lineage and Integrity Audit

## 1. Executive Summary

| Audit Item | Baseline / Current Measurement | Integrity Classification |
| :--- | :--- | :---: |
| **Audit Phase** | Phase P2.5.3 — Financial Remediation Lineage & Integrity Audit | — |
| **Target Repository** | `C:\Users\vigne\OneDrive\Desktop\projects\swing-trading-tool` | — |
| **Verified Baseline Commit** | `ecbcbde2e78f03e06575b84240634ba3b5c81239` | **PASS** |
| **Production Database (`swing_trading.db`) Hash** | `1a2036fcc72af59b3633b5c2a077c26dd45756b3360824f36e995e2e805a28a8` | **PASS** (Zero Modifications) |
| **Staging Database (`staging_financial_expansion.db`) Hash** | `6ea5a58bce4accd276255794b8e2001c68adeedb79daf2804d1d16a94f698e7b` | **PASS** (Read-Only Audit) |
| **Total Staging Records Audited** | 17 Vintages (10 Original Pilot + 7 Remediation Vintages) | **PASS** |
| **Original Pilot Records Preservation** | 10 / 10 Preserved (Zero Deletions) | **PASS** |
| **Filing Type vs Internal Revision Semantics** | Conflated in `filing_type` (Corporate Event vs Internal Pipeline Correction) | **FAIL** |
| **Point-in-Time (PIT) Window Ranking Correctness** | Correctly filters `effective_trading_date <= eval_date` | **PASS WITH CONDITIONS** |
| **HDFC Bank Scope & Sector Metrics Consistency** | NII/CAR/NPA copied between Standalone & Consolidated; Q1 Standalone Top-line retained | **FAIL** |
| **Revenue Normalization (Reliance & Adani)** | Operations vs Gross vs Total Income separated mathematically | **PASS WITH CONDITIONS** |
| **Filing Document Authenticity** | All 10 stored `.pdf` files are 113–135 byte mock test strings; original binaries absent | **UNVERIFIED** |
| **Final Milestone Verdict** | **`P2.5.3 COMPLETE — DATA INTEGRITY ISSUES REMAIN`** | — |

---

## 2. Full 17-Vintage Audit Matrix

The staging table `quarterly_financial_vintages` was audited across all 17 persisted rows. The matrix below captures the complete audit footprint:

| ID | Symbol | Quarter | Scope | Filing Type | Ver | Superseded By | Publication Timestamp | Effective Trading Date | Revenue (₹ Cr) | PAT (₹ Cr) | D/E | Net Interest Income | Status | Remediation Type | Audit Finding |
| :---: | :--- | :--- | :--- | :--- | :---: | :---: | :--- | :--- | :---: | :---: | :---: | :---: | :---: | :--- | :--- |
| **1** | TCS | 2024-Q1 | CONSOLIDATED | ORIGINAL | 1 | — | 2024-07-11 17:30:00 | 2024-07-12 | 62,613.00 | 12,040.00 | 0.00 | NULL | VERIFIED | ORIGINAL_PILOT | **PASS WITH CONDITIONS**: Authentic values; mock PDF artifact. |
| **2** | TCS | 2024-Q2 | CONSOLIDATED | ORIGINAL | 1 | — | 2024-10-10 17:30:00 | 2024-10-11 | 64,259.00 | 11,909.00 | 0.00 | NULL | VERIFIED | ORIGINAL_PILOT | **PASS WITH CONDITIONS**: Authentic values; mock PDF artifact. |
| **3** | INFY | 2024-Q1 | CONSOLIDATED | ORIGINAL | 1 | — | 2024-07-18 15:45:00 | 2024-07-19 | 39,315.00 | 6,368.00 | 0.00 | NULL | VERIFIED | ORIGINAL_PILOT | **PASS WITH CONDITIONS**: Authentic values; mock PDF artifact. |
| **4** | INFY | 2024-Q2 | CONSOLIDATED | ORIGINAL | 1 | — | 2024-10-17 15:45:00 | 2024-10-18 | 40,986.00 | 6,506.00 | 0.00 | NULL | VERIFIED | ORIGINAL_PILOT | **PASS WITH CONDITIONS**: Authentic values; mock PDF artifact. |
| **5** | RELIANCE | 2024-Q1 | CONSOLIDATED | ORIGINAL | 1 | **11** | 2024-07-19 18:00:00 | 2024-07-22 | 257,823.00 | 17,448.00 | 0.4074 | NULL | VERIFIED | ORIGINAL_PILOT | **SUPERSEDED**: Revenue stored gross turnover instead of core operations. |
| **6** | RELIANCE | 2024-Q2 | CONSOLIDATED | ORIGINAL | 1 | **12** | 2024-10-14 18:00:00 | 2024-10-15 | 235,481.00 | 16,563.00 | 0.4061 | NULL | VERIFIED | ORIGINAL_PILOT | **SUPERSEDED**: Lacked disaggregated turnover breakdown. |
| **7** | HDFCBANK | 2024-Q1 | CONSOLIDATED | ORIGINAL | 1 | **15** | 2024-07-20 12:30:00 | 2024-07-22 | 83,701.00 | 16,474.00 | 6.3636 | NULL | VERIFIED | ORIGINAL_PILOT | **SUPERSEDED**: Non-financial D/E applied; deposits treated as corporate debt. |
| **8** | HDFCBANK | 2024-Q2 | CONSOLIDATED | ORIGINAL | 1 | **16** | 2024-10-19 12:30:00 | 2024-10-21 | 85,499.00 | 17,830.00 | 6.2637 | NULL | VERIFIED | ORIGINAL_PILOT | **SUPERSEDED**: Scope mismatch (Standalone revenue with Consolidated PAT). |
| **9** | ADANIENT | 2024-Q1 | CONSOLIDATED | ORIGINAL | 1 | **13** | 2024-08-01 14:15:00 | 2024-08-01 | 26,067.00 | 1,455.00 | 1.3810 | NULL | VERIFIED | ORIGINAL_PILOT | **SUPERSEDED**: Total Income stored in `revenue` instead of core ops. |
| **10** | ADANIENT | 2024-Q2 | CONSOLIDATED | ORIGINAL | 1 | **14** | 2024-10-29 14:15:00 | 2024-10-29 | 22,608.00 | 1,742.00 | 1.3636 | NULL | VERIFIED | ORIGINAL_PILOT | **SUPERSEDED**: Lacked total income breakdown. |
| **11** | RELIANCE | 2024-Q1 | CONSOLIDATED | RESTATED | 2 | — | 2024-07-19 18:00:00 | 2024-07-22 | 236,217.00 | 17,448.00 | 0.4074 | NULL | VERIFIED | INTERNAL_EXTRACTION_CORRECTION | **PASS WITH CONDITIONS**: Net Revenue ₹236,217 Cr normalized; `filing_type` incorrectly labeled RESTATED. |
| **12** | RELIANCE | 2024-Q2 | CONSOLIDATED | RESTATED | 2 | — | 2024-10-14 18:00:00 | 2024-10-15 | 235,481.00 | 16,563.00 | 0.4061 | NULL | VERIFIED | INTERNAL_EXTRACTION_CORRECTION | **PASS WITH CONDITIONS**: Metadata enriched; `filing_type` incorrectly labeled RESTATED. |
| **13** | ADANIENT | 2024-Q1 | CONSOLIDATED | RESTATED | 2 | — | 2024-08-01 14:15:00 | 2024-08-01 | 25,472.40 | 1,455.00 | 1.3810 | NULL | VERIFIED | INTERNAL_EXTRACTION_CORRECTION | **PASS WITH CONDITIONS**: Core ops ₹25,472.40 Cr isolated; `filing_type` incorrectly labeled RESTATED. |
| **14** | ADANIENT | 2024-Q2 | CONSOLIDATED | RESTATED | 2 | — | 2024-10-29 14:15:00 | 2024-10-29 | 22,608.00 | 1,742.00 | 1.3636 | NULL | VERIFIED | INTERNAL_EXTRACTION_CORRECTION | **PASS WITH CONDITIONS**: Total Income ₹23,196 Cr metadata enriched. |
| **15** | HDFCBANK | 2024-Q1 | CONSOLIDATED | RESTATED | 2 | — | 2024-07-20 12:30:00 | 2024-07-22 | 83,701.25 | 16,474.85 | NULL | 29,837.00 | VERIFIED | SECTOR_BANKING_METRICS_REMEDIATION | **FAIL**: Revenue is Standalone (₹83,701.25 Cr) under Consolidated scope; NII copied from Standalone. |
| **16** | HDFCBANK | 2024-Q2 | CONSOLIDATED | RESTATED | 2 | — | 2024-10-19 12:30:00 | 2024-10-21 | 121,457.00 | 17,830.00 | NULL | 30,111.00 | VERIFIED | SCOPE_ALIGNMENT_CORRECTION | **FAIL**: Standalone NII (₹30,111 Cr) and Standalone CRAR/NPA copied into Consolidated scope. |
| **17** | HDFCBANK | 2024-Q2 | STANDALONE | ORIGINAL | 1 | — | 2024-10-19 12:30:00 | 2024-10-21 | 85,499.64 | 16,821.00 | NULL | 30,111.00 | VERIFIED | SCOPE_ALIGNMENT_CORRECTION | **PASS WITH CONDITIONS**: Standalone metrics authentic; source PDF is test fixture. |

---

## 3. Filing Type vs. Internal Correction Analysis

### The Semantic Conflation Defect
A fundamental design flaw identified during this audit is the **conflation of company-announced disclosure categories with internal pipeline data corrections**.

In Indian corporate reporting governed by SEBI (Listing Obligations and Disclosure Requirements) Regulations, 2015:
- **`ORIGINAL`**: The primary unaudited or audited financial results submitted by the company within 45 days of the quarter-end under Regulation 33.
- **`AMENDED` / `REVISED`**: A revised filing submitted by the company to the stock exchange to correct clerical errors, typographical omissions, or disclosure gaps in the original broadcast.
- **`RESTATED`**: A retrospective restatement of historical accounts published in an Information Memorandum, Rights Issue Draft Letter of Offer, or Scheme of Amalgamation (e.g., following a merger or accounting policy change under Ind AS 8).
- **`AUDITED_FINAL`**: The annual audited financial statements replacing quarterly limited reviews.

### Current Implementation Flaw
In records 11, 12, 13, 14, 15, and 16:
- The staging pipeline marked `filing_type = 'RESTATED'`.
- **Reality:** Reliance, Adani Enterprises, and HDFC Bank **did not file restated financials** on the exchange. The exchange disclosures were and remain `ORIGINAL` Regulation 33 filings.
- The reason for inserting version 2 was an **internal parser extraction error** (Reliance gross vs net turnover; Adani other income mix-up; HDFC Bank standalone top-line copy).
- Because `quarterly_financial_vintages` had a database check constraint `CHECK(filing_type IN ('ORIGINAL', 'AMENDED', 'RESTATED', 'AUDITED_FINAL'))`, P2.5.2 populated `filing_type = 'RESTATED'` to satisfy the check constraint while adding `remediation_type = 'INTERNAL_EXTRACTION_CORRECTION'`.

### Recommended Semantic Separation
The database must establish four distinct, uncoupled columns:

```
[Company-Announced Event]         [Data Engineering Lifecycle]      [Data Governance]          [Trading Platform Engine]
      filing_type                  pipeline_revision_type          verification_status            research_eligibility
───────────────────────────       ──────────────────────────────   ──────────────────────     ─────────────────────────────
• ORIGINAL                        • INITIAL_INGESTION              • VERIFIED                 • ELIGIBLE
• REVISED_DISCLOSURE              • EXTRACTION_CORRECTION          • PROVISIONAL              • INELIGIBLE_SOURCE_PENDING
• CORPORATE_RESTATEMENT           • SCOPE_REALIGNMENT              • AUDIT_FLAGGED            • QUARANTINED_ANOMALOUS
• ANNUAL_AUDITED_FINAL            • SECTOR_SCHEMA_BACKPORT         • REJECTED                 • SUPERSEDED_INACTIVE
```

### Demonstration on Existing Remediation Records

| Record ID | Symbol / Quarter | Current Defective State | Corrected Company Filing Type | Corrected Pipeline Revision Type | Corrected Research Eligibility |
| :---: | :--- | :--- | :--- | :--- | :--- |
| **5** | RELIANCE 24-Q1 | `filing_type='ORIGINAL', verification_status='VERIFIED'` | `ORIGINAL` | `INITIAL_INGESTION` | `SUPERSEDED_INACTIVE` |
| **11** | RELIANCE 24-Q1 | `filing_type='RESTATED', remediation_type='INTERNAL_...'` | `ORIGINAL` | `EXTRACTION_CORRECTION` | `ELIGIBLE` (Pending binary doc) |
| **7** | HDFCBANK 24-Q1 | `filing_type='ORIGINAL', verification_status='VERIFIED'` | `ORIGINAL` | `INITIAL_INGESTION` | `SUPERSEDED_INACTIVE` |
| **15** | HDFCBANK 24-Q1 | `filing_type='RESTATED', remediation_type='SECTOR_...'` | `ORIGINAL` | `SECTOR_SCHEMA_BACKPORT` | `INELIGIBLE_SOURCE_PENDING` (Scope flaw) |
| **16** | HDFCBANK 24-Q2 | `filing_type='RESTATED', remediation_type='SCOPE_...'` | `ORIGINAL` | `SCOPE_REALIGNMENT` | `INELIGIBLE_SOURCE_PENDING` (NII copy flaw) |
| **17** | HDFCBANK 24-Q2 | `filing_type='ORIGINAL', remediation_type='SCOPE_...'` | `ORIGINAL` | `INITIAL_INGESTION` | `ELIGIBLE` (Pending binary doc) |

---

## 4. Historical Point-in-Time (PIT) Integrity & Query Analysis

The PIT query in `StagingFinancialVintageRepository.get_point_in_time_vintages()` was inspected and evaluated across six operational market timing scenarios:

```sql
WITH eligible_vintages AS (
    SELECT 
        v.*, c.symbol,
        ROW_NUMBER() OVER (
            PARTITION BY v.quarter 
            ORDER BY v.version_sequence DESC, v.publication_timestamp DESC
        ) AS rank
    FROM quarterly_financial_vintages v
    INNER JOIN companies c ON v.company_id = c.id
    WHERE c.symbol = ?
      AND v.filing_scope = ?
      AND v.effective_trading_date <= ?
      AND v.verification_status = 'VERIFIED'
)
SELECT * FROM eligible_vintages WHERE rank = 1 ORDER BY period_end_date ASC;
```

### Scenario Evaluation Results

| Scenario | Evaluation Date | Target Symbol / Quarter | Query Result | Lookahead Assessment | Classification |
| :--- | :---: | :---: | :---: | :--- | :---: |
| **1. Pre-Publication** | `2024-07-15` | RELIANCE Q1 (Pub: `2024-07-19`) | `0 records returned` | **Zero Leakage:** Strictly excludes unannounced filings. | **PASS** |
| **2. On Effective Date** | `2024-07-22` | RELIANCE Q1 (Eff: `2024-07-22`) | Returns Vintage 11 (`₹236,217 Cr`) | **Valid for Extraction Fix:** Market had real figure on July 22. | **PASS WITH CONDITIONS** |
| **3. Mid-Period** | `2024-08-15` | RELIANCE Q1 & Q2 | Returns only Q1 (Vintage 11) | **Zero Leakage:** Q2 (Eff: `2024-10-15`) excluded. | **PASS** |
| **4. Post-Q2 Announcement** | `2024-10-20` | RELIANCE Q1 & Q2 | Returns Q1 (v2) & Q2 (v2) | Correct point-in-time progression. | **PASS** |
| **5. Company Restatement** | `2024-08-15` | Hypothetical Corporate Restatement | Would return v2 prematurely if labeled RESTATED | **High Risk:** Internal fixes sharing original timestamps would leak future restatements if not separated. | **FAIL** |
| **6. Scope Isolation** | `2024-11-04` | HDFCBANK Standalone vs Cons. | Completely isolated | Standalone query returns Vintage 17; Cons returns 15 & 16. | **PASS** |

### Critical Finding on Lookahead Integrity
If a data correction only fixes an internal extraction error to match what the company genuinely published on day one, applying that correction to the original effective trading date **does not constitute financial lookahead bias**, because public market participants had access to those authentic numbers on that exact date.

**However**, if a company genuinely files an amended or restated result months later (e.g. November 2024), that restatement **must never inherit the original July 2024 effective trading date**. The current codebase relies on manually setting `effective_trading_date`. Because P2.5.2 populated `filing_type = 'RESTATED'` while assigning the original July 2024 effective date, an automated engine cannot differentiate an internal pipeline bug-fix from a true corporate restatement.

---

## 5. HDFC Banking Metrics Audit

An independent audit of HDFCBANK Q1 and Q2 records revealed **two critical data integrity defects**:

### Defect 1: Standalone Metric Copying into Consolidated Scope
In commercial banking, banking-specific performance metrics (Net Interest Income, Capital Adequacy Ratio, Gross NPA, Net NPA) are statutory disclosures regulated by the Reserve Bank of India (RBI) and reported specifically for the **parent banking entity (Standalone)**:
- In Vintage 16 (HDFCBANK Q2 Consolidated):
  - `net_interest_income` is recorded as `₹30,111.00 Cr`.
  - **Audit Fact:** `₹30,111.00 Cr` is the **Standalone NII** of HDFC Bank Limited. Consolidated disclosures include insurance premiums from HDFC Life, asset management fees from HDFC AMC, and general insurance income from HDFC ERGO. Consolidated financial statements do not report a simple single NII figure identical to the parent bank.
  - `capital_adequacy_ratio` is recorded as `19.80%` in both Vintage 16 (Consolidated) and Vintage 17 (Standalone). In official filings, Standalone CAR was 19.80%, whereas Consolidated CAR was 19.30%.
  - `gross_npa_pct` (`1.36%`) and `net_npa_pct` (`0.41%`) are Standalone banking asset quality metrics. The banking group does not calculate NPAs for non-lending subsidiaries.

### Defect 2: HDFC Bank Q1 FY25 Revenue Scope Mismatch Retained
- In Vintage 15 (HDFCBANK Q1 Consolidated, v2):
  - `revenue` is recorded as `₹83,701.25 Cr`.
  - `total_income` is recorded as `₹83,701.25 Cr`.
  - `net_profit` is recorded as `₹16,474.85 Cr`.
- **Audit Fact:** `₹83,701.25 Cr` is **Standalone Total Income** (Interest Earned ₹73,295 Cr + Other Income ₹10,406 Cr). Consolidated Total Income for Q1 FY25 was approximately `₹118,500 Cr`, while Consolidated PAT was `₹16,474.85 Cr` (Standalone PAT was `₹16,175.00 Cr`).
- **Conclusion:** While P2.5.2 successfully fixed the scope mismatch for Q2 (Vintage 16 vs 17), **it failed to fix the scope mismatch for Q1 (Vintage 15)**. Vintage 15 still pairs Standalone Total Income (`₹83,701.25 Cr`) with Consolidated PAT (`₹16,474.85 Cr`).

### Defect 3: Non-Financial Ratios on Banking Records
- In Vintages 7 and 8 (Original Pilot):
  - `total_debt` was recorded as `₹28,00,000 Cr` and `₹28,50,000 Cr`.
  - `debt_equity` was computed as `6.36x` and `6.26x`.
  - **Audit Finding:** Customer deposits (`₹23,79,100 Cr`) were classified as corporate debt. Commercial bank deposits are liabilities, but treating them as corporate debt triggers invalid solvency red flags.
  - While Vintages 15, 16, and 17 correctly nullified `debt_equity`, Vintages 7 and 8 retain these invalid ratios under `verification_status = 'VERIFIED'`.

---

## 6. Revenue Normalization Audit

The revenue figures for Reliance Industries and Adani Enterprises were audited for line-item disaggregation and non-double-counting:

### Reliance Industries Normalization
- **Q1 FY25 (Vintage 11, v2):**
  - Gross Turnover: `₹257,823.00 Cr`
  - Deductions (GST & Excise Duty): `₹21,606.00 Cr`
  - **Net Revenue from Operations:** `₹236,217.00 Cr`
  - Other Income: `₹3,639.00 Cr`
  - **Total Income:** `₹239,856.00 Cr` (`236,217.00 + 3,639.00`)
  - Operating Profit: `₹42,748.00 Cr`
  - Operating Margin: `0.1810` (`42,748 / 236,217`)
  - **Audit Verdict:** **PASS WITH CONDITIONS**. Disaggregation is mathematically consistent and correctly isolates excise deductions. However, figures are derived from external secondary consensus; primary binary PDF proof is absent in `database/staging_filings_store/`.
- **Q2 FY25 (Vintage 12, v2):**
  - Gross Turnover: `₹258,027.00 Cr`
  - Deductions (GST & Excise Duty): `₹22,546.00 Cr`
  - **Net Revenue from Operations:** `₹235,481.00 Cr`
  - Other Income: `₹4,835.00 Cr`
  - **Total Income:** `₹240,316.00 Cr` (`235,481.00 + 4,835.00`)
  - Operating Profit: `₹43,934.00 Cr`
  - Operating Margin: `0.1866` (`43,934 / 235,481`)
  - **Audit Verdict:** **PASS WITH CONDITIONS**.

### Adani Enterprises Normalization
- **Q1 FY25 (Vintage 13, v2):**
  - **Revenue from Operations:** `₹25,472.40 Cr`
  - Other Income: `₹594.60 Cr`
  - **Total Income:** `₹26,067.00 Cr` (`25,472.40 + 594.60`)
  - Operating Profit: `₹4,300.00 Cr`
  - Operating Margin: `0.1688` (`4,300 / 25,472.40`)
  - **Audit Verdict:** **PASS WITH CONDITIONS**. Correctly strips Other Income out of operating revenue.
- **Q2 FY25 (Vintage 14, v2):**
  - **Revenue from Operations:** `₹22,608.00 Cr`
  - Other Income: `₹588.00 Cr`
  - **Total Income:** `₹23,196.00 Cr` (`22,608.00 + 588.00`)
  - Operating Profit: `₹4,158.00 Cr`
  - Operating Margin: `0.1839` (`4,158 / 22,608.00`)
  - **Audit Verdict:** **PASS WITH CONDITIONS**.

---

## 7. Document Authenticity Status

Physical examination of the staging file storage directory (`database/staging_filings_store/`) was conducted:

### Physical Artifact Inspection

| Company Folder | File Name | Size (Bytes) | Header Content Inspection | Authenticity Classification |
| :--- | :--- | :---: | :--- | :---: |
| `TCS/` | `TCS_2024-Q1_547a7b30ecff_TCS_Q1_FY25_Results.pdf` | 113 B | `b'%PDF-1.4 TCS Limited Financial Results for the quarter ended June 30 2024 Revenue 62613 Cr...'` | **TEST_MOCK_ARTIFACT** |
| `TCS/` | `TCS_2024-Q2_f513cf1d9717_TCS_Q2_FY25_Results.pdf` | 118 B | `b'%PDF-1.4 TCS Limited Financial Results for the quarter ended September 30 2024 Revenue 64259 Cr...'` | **TEST_MOCK_ARTIFACT** |
| `INFY/` | `INFY_2024-Q1_6d743732df4b_INFY_Q1_FY25_Results.pdf` | 116 B | `b'%PDF-1.4 Infosys Limited Financial Results for the quarter ended June 30 2024 Revenue 39315 Cr...'` | **TEST_MOCK_ARTIFACT** |
| `INFY/` | `INFY_2024-Q2_c4c04a774111_INFY_Q2_FY25_Results.pdf` | 121 B | `b'%PDF-1.4 Infosys Limited Financial Results for the quarter ended September 30 2024 Revenue 40986 Cr...'` | **TEST_MOCK_ARTIFACT** |
| `RELIANCE/` | `RELIANCE_2024-Q1_e1f331263a2e_RELIANCE_Q1_FY25_Results.pdf` | 130 B | `b'%PDF-1.4 Reliance Industries Limited Financial Results for the quarter ended June 30 2024 Revenue 257823 Cr...'` | **TEST_MOCK_ARTIFACT** |
| `RELIANCE/` | `RELIANCE_2024-Q2_690b0e8a4364_RELIANCE_Q2_FY25_Results.pdf` | 135 B | `b'%PDF-1.4 Reliance Industries Limited Financial Results for the quarter ended September 30 2024 Revenue 235481 Cr...'` | **TEST_MOCK_ARTIFACT** |
| `HDFCBANK/` | `HDFCBANK_2024-Q1_b0fa99178e19_HDFCBANK_Q1_FY25_Results.pdf` | 119 B | `b'%PDF-1.4 HDFC Bank Limited Financial Results for the quarter ended June 30 2024 Revenue 83701 Cr...'` | **TEST_MOCK_ARTIFACT** |
| `HDFCBANK/` | `HDFCBANK_2024-Q2_afbb96403d8a_HDFCBANK_Q2_FY25_Results.pdf` | 124 B | `b'%PDF-1.4 HDFC Bank Limited Financial Results for the quarter ended September 30 2024 Revenue 85499 Cr...'` | **TEST_MOCK_ARTIFACT** |
| `ADANIENT/` | `ADANIENT_2024-Q1_d73361ce204d_ADANIENT_Q1_FY25_Results.pdf` | 126 B | `b'%PDF-1.4 Adani Enterprises Limited Financial Results for the quarter ended June 30 2024 Revenue 26067 Cr...'` | **TEST_MOCK_ARTIFACT** |
| `ADANIENT/` | `ADANIENT_2024-Q2_82f2604c46b7_ADANIENT_Q2_FY25_Results.pdf` | 131 B | `b'%PDF-1.4 Adani Enterprises Limited Financial Results for the quarter ended September 30 2024 Revenue 22608 Cr...'` | **TEST_MOCK_ARTIFACT** |

### Integrity Audit Findings on Storage
1. **Zero Authentic Binary Documents:** There is **not a single authentic binary exchange disclosure** stored locally. All ten files are 113–135 byte single-line ASCII strings generated as pipeline test scaffolding.
2. **Hash Mismatch to Real Filings:** The SHA-256 fingerprints recorded in `source_document_hash` (e.g. `547a7b30ecff...` for TCS Q1) hash the 113-byte ASCII test fixture, **not** the official multi-megabyte signed disclosure PDF published on the NSE archive.
3. **Artifact Discrepancy:** The mock text artifact for Reliance Q1 (`...Revenue 257823 Cr...`) still contains the old un-normalized gross revenue figure, even though Vintage 11 in the database references this hash with `revenue = 236217.0`.
4. **Current Status:** Correctly identified in sidecar metadata as `TEST_MOCK_ARTIFACT` with `retrieval_status = SOURCE_DOCUMENT_UNAVAILABLE`.

---

## 8. Data Eligibility Recommendations

Based on the audit findings, financial vintages must be assigned clear operational eligibility flags:

```
+──────────────────────────+───────────────────────────────────────────────+──────────────────────────────+
| Eligibility Tier         | Condition / Criteria                          | Allowed Engine Consumers     |
+──────────────────────────+───────────────────────────────────────────────+──────────────────────────────+
| TIER 1: VERIFIED_ELIGIBLE| Authentic binary exchange PDF preserved;      | Live Signals, Backtesting,   |
|                          | full line items verified against PDF.         | Opportunity Scoring, APIs    |
+──────────────────────────+───────────────────────────────────────────────+──────────────────────────────+
| TIER 2: PROVISIONAL_DEMO | Authentic numerical values from exchange;     | Sandbox / Staging Testing    |
|                          | mock PDF fixture preserved locally.           | (BLOCKED from Live Trading)  |
+──────────────────────────+───────────────────────────────────────────────+──────────────────────────────+
| TIER 3: QUARANTINED      | Scope mix-up, metric copying between scopes,  | Research Audit Only          |
|                          | or un-normalized line items.                  | (BLOCKED from all engines)   |
+──────────────────────────+───────────────────────────────────────────────+──────────────────────────────+
| TIER 4: SUPERSEDED       | Replaced by a subsequent valid vintage.       | Audit Lineage Only           |
+──────────────────────────+───────────────────────────────────────────────+──────────────────────────────+
```

### Assignment for Audited 17 Vintages:
- **TIER 2 (PROVISIONAL_DEMO):** Vintages 1, 2, 3, 4 (TCS, INFY), 11, 12 (RELIANCE), 13, 14 (ADANIENT), 17 (HDFCBANK Standalone). Authentic reported values, but lack preserved binary exchange PDFs.
- **TIER 3 (QUARANTINED):** Vintages 15 and 16 (HDFCBANK Consolidated). Must be quarantined due to scope mismatch in Q1 and Standalone NII/NPA copying in Q2.
- **TIER 4 (SUPERSEDED):** Vintages 5, 6, 7, 8, 9, 10.

---

## 9. Required Schema Improvements (Prior to Production Migration)

Before promoting `quarterly_financial_vintages` to production, the following schema improvements must be implemented:

```sql
-- RECOMMENDED SCHEMA ARCHITECTURE FOR PHASE P2.6
CREATE TABLE quarterly_financial_vintages (
    id                          INTEGER PRIMARY KEY AUTOINCREMENT,
    company_id                  INTEGER NOT NULL,
    quarter                     TEXT NOT NULL,               -- 'YYYY-Q1'
    period_start_date           TEXT NOT NULL,               -- 'YYYY-MM-DD'
    period_end_date             TEXT NOT NULL,               -- 'YYYY-MM-DD'
    accounting_standard         TEXT NOT NULL DEFAULT 'IND_AS',
    filing_scope                TEXT NOT NULL CHECK(filing_scope IN ('CONSOLIDATED', 'STANDALONE')),
    
    -- 1. Clean Separation: Company Filing Type vs Internal Revision Type
    company_filing_type         TEXT NOT NULL CHECK(company_filing_type IN (
                                    'ORIGINAL', 'REVISED_DISCLOSURE', 'CORPORATE_RESTATEMENT', 'ANNUAL_AUDITED_FINAL'
                                )),
    internal_revision_type      TEXT NOT NULL DEFAULT 'INITIAL_INGESTION' CHECK(internal_revision_type IN (
                                    'INITIAL_INGESTION', 'EXTRACTION_CORRECTION', 'SCOPE_REALIGNMENT', 'SECTOR_NORMALIZATION'
                                )),
    version_sequence            INTEGER NOT NULL DEFAULT 1,
    superseded_by_vintage_id    INTEGER,
    
    -- 2. Publication & Timestamps
    exchange                    TEXT NOT NULL CHECK(exchange IN ('NSE', 'BSE')),
    exchange_broadcast_id       TEXT NOT NULL,
    original_broadcast_id       TEXT,
    publication_timestamp       TEXT NOT NULL,               -- Time company broadcasted to exchange
    effective_trading_date      TEXT NOT NULL,               -- First executable market session
    pipeline_ingested_at        TEXT DEFAULT CURRENT_TIMESTAMP,
    
    -- 3. Disaggregated Operating Financials (in INR Crores)
    revenue                     REAL NOT NULL,               -- Standardized Revenue from Operations
    revenue_from_operations     REAL,                        -- Disclosed Net Revenue
    gross_revenue               REAL,                        -- Gross turnover before duties
    total_income                REAL,                        -- Turnover + Other Income
    operating_expenses          REAL,
    operating_profit            REAL,
    net_profit                  REAL NOT NULL,               -- PAT attributable to owners
    eps                         REAL NOT NULL,
    
    -- 4. Sector-Aware Banking Line Items (Strictly NULL for Non-Banks)
    is_banking_institution      INTEGER NOT NULL DEFAULT 0,
    net_interest_income         REAL,                        -- Bank NII
    customer_deposits           REAL,                        -- Bank Deposits
    capital_adequacy_ratio      REAL,                        -- Bank CRAR (%)
    gross_npa_pct               REAL,                        -- Bank Gross NPA (%)
    net_npa_pct                 REAL,                        -- Bank Net NPA (%)
    
    -- 5. Standard Balance Sheet Line Items (NULL for Banks)
    total_assets                REAL,
    total_equity                REAL,
    total_debt                  REAL,                        -- Corporate borrowings (excluding bank deposits)
    current_liabilities         REAL,
    
    -- 6. Materialized Financial Ratios
    roe                         REAL,
    roce                        REAL,                        -- NULL for Banks
    debt_equity                 REAL,                        -- NULL for Banks
    operating_margin            REAL,
    net_margin                  REAL,
    
    -- 7. Document Provenance & Research Governance
    source_document_url         TEXT NOT NULL,
    source_document_hash        TEXT NOT NULL,               -- SHA-256 of preserved file
    document_classification     TEXT NOT NULL CHECK(document_classification IN (
                                    'AUTHENTIC_BINARY_PDF', 'TEST_MOCK_ARTIFACT', 'XBRL_INSTANCE_DOCUMENT'
                                )),
    verification_status         TEXT NOT NULL CHECK(verification_status IN (
                                    'VERIFIED', 'PROVISIONAL', 'REJECTED'
                                )),
    research_eligibility        TEXT NOT NULL DEFAULT 'INELIGIBLE_SOURCE_PENDING' CHECK(research_eligibility IN (
                                    'VERIFIED_ELIGIBLE', 'PROVISIONAL_DEMO', 'QUARANTINED', 'SUPERSEDED'
                                )),
    remediation_notes           TEXT,
    
    FOREIGN KEY (company_id) REFERENCES companies(id),
    FOREIGN KEY (superseded_by_vintage_id) REFERENCES quarterly_financial_vintages(id),
    UNIQUE(exchange, exchange_broadcast_id),
    UNIQUE(company_id, quarter, filing_scope, version_sequence)
);
```

---

## 10. Final Phase Recommendation

### Summary of Audit Classification
- **Database Safety & Isolation:** **PASS** (Zero production or staging mutations).
- **Append-Only Preservation:** **PASS** (10 original pilot records preserved intact).
- **Lineage Supersession:** **PASS** (Superseded pointers correctly resolve to v2 records).
- **Revenue Normalization:** **PASS WITH CONDITIONS** (Mathematically correct; source unverified).
- **Filing Type Semantics:** **FAIL** (`filing_type` conflates corporate restatements with internal bug fixes).
- **HDFC Banking Metrics:** **FAIL** (Q1 retains standalone revenue under consolidated scope; Q2 copies standalone NII/NPA into consolidated).
- **Source Document Authenticity:** **UNVERIFIED** (All files are mock text fixtures).

### Final Recommendation
The pilot has validated the architectural mechanics of append-only versioning, PIT lookup indexing, and ratio derivation. However, **the data layer is not yet ready for production promotion or universe expansion**.

Before proceeding to P2.6, the following remediation steps must be completed:
1. Re-align HDFC Bank Q1 Consolidated top-line to genuine consolidated total income (`~₹118,500 Cr`).
2. Separate Standalone banking metrics (NII, CAR, NPA) from Consolidated scope records.
3. Adopt the proposed four-tier schema separation (`company_filing_type`, `internal_revision_type`, `verification_status`, `research_eligibility`).
4. Establish an authentic, session-authenticated binary filing retrieval pipeline to replace mock text files with authentic exchange PDFs.

---

## 11. Final Audit Verification Proof

```
========================================================================================
FINAL VERIFICATION AUDIT TRAIL
========================================================================================
- Production Database Path:        database/swing_trading.db
- Production Hash (Before Audit):  1a2036fcc72af59b3633b5c2a077c26dd45756b3360824f36e995e2e805a28a8
- Production Hash (After Audit):   1a2036fcc72af59b3633b5c2a077c26dd45756b3360824f36e995e2e805a28a8
- Production Record Count:         260 rows in quarterly_results (100% UNTOUCHED)

- Staging Database Path:           database/staging_financial_expansion.db
- Staging Hash (Before Audit):     6ea5a58bce4accd276255794b8e2001c68adeedb79daf2804d1d16a94f698e7b
- Staging Hash (After Audit):      6ea5a58bce4accd276255794b8e2001c68adeedb79daf2804d1d16a94f698e7b
- Staging Record Count:            17 rows in quarterly_financial_vintages (100% UNTOUCHED)

- Protected Files Status:          strategy_engine.py (non-existent)
                                   signal_engine.py (0 modifications)
                                   trade_quality_engine.py (0 modifications)
                                   portfolio_simulator.py (0 modifications)

- Deliverable Created:             docs/audit_artifacts/P2_5_3_REMEDIATION_LINEAGE_AUDIT.md
- Database Modifications:          0 (Zero)
- Ingestion Module Modifications:  0 (Zero)
- Engine Modifications:            0 (Zero)
- Git Commits Created:             0 (Zero)
- Git Pushes Executed:             0 (Zero)
========================================================================================
FINAL VERDICT: P2.5.3 COMPLETE — DATA INTEGRITY ISSUES REMAIN
========================================================================================
```

