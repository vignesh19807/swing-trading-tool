# P2.8 — Scope-Safe Financial Parsing & Banking Normalization Report

## 1. Overview & Objectives

Phase P2.8 enforces reporting scope safety and sector-aware accounting normalizations across corporate and banking financial statements:
- Preservation of scope metadata: `filing_scope` (`CONSOLIDATED` vs `STANDALONE`).
- Detailed revenue breakdown: `revenue_from_operations`, `gross_revenue`, `other_income`, `total_income`.
- Clear profit allocation: Profit After Tax (PAT) attributable to shareholders/owners of the parent company.
- Specialized commercial banking line items: Customer deposits, net interest income (NII), net interest margin (NIM), capital adequacy ratio (CRAR), Gross NPA (%), Net NPA (%), Gross Advances, Provision Coverage Ratio (PCR).
- Invariant Solvency Rules for Banks: Conventional corporate Debt-to-Equity ($D/E$) and ROCE are strictly enforced as `NULL`. Customer deposits are segregated from borrowings.
- Scope-mixing prohibition: Standalone metrics are strictly prohibited from being copied into consolidated records.

---

## 2. Implementation Architecture

Implemented in `backend/data_pipeline/financial_filing_parser.py`:
- `ScopeSafeFilingParser.parse_filing_payload(raw_payload)`:
  - Validates `filing_scope` in `('CONSOLIDATED', 'STANDALONE')`.
  - Normalizes reported monetary quantities into standardized **INR Crores** using deterministic unit conversion factors (`CRORES`: 1.0, `LAKHS`: 0.01, `INR`: $10^{-7}$).
  - Enforces corporate vs banking branching:
    - If `is_bank` is True:
      - `revenue` maps to Total Income.
      - `debt_equity = None`, `roce = None`, `total_debt = None`.
      - Customer deposits and banking ratios preserved.
      - Raises `ValueError` if `is_scope_mixed` is detected.
    - If `is_bank` is False:
      - `revenue_from_operations` is primary.
      - $D/E = \text{Total Debt} / \text{Total Equity}$.
      - $\text{ROCE} = \text{Operating Profit} / (\text{Total Assets} - \text{Current Liabilities})$.

---

## 3. HDFC Remediation Audit & Historical Vintage Review

Vintages 7, 8, 15, 16, and 17 in `database/staging_financial_expansion.db` were audited:

### Pre-Existing Vintages Review:
- **Vintage 7 & 8 (Original Pilot)**: Flawed extraction where corporate D/E and ROCE were computed on a commercial bank. Already marked `REJECTED` and `SUPERSEDED` by 15 and 16.
- **Vintage 15 & 16 (Remediation V2)**: Remediated to isolate banking solvency, but audit defect finding P2.5.3 correctly flagged scope ambiguity (retaining standalone top-line figures in Q1 and borrowing standalone banking metrics in Q2). Marked `REJECTED` and `QUARANTINED`.
- **Vintage 17 (Standalone Q2)**: Correctly isolated standalone banking filing. Retained as `PROVISIONAL_DEMO`.

### Authentic Ingestion & Current Disposition:
- Authentic filings for HDFCBANK (NSE Announcements 163625 and 165745) were retrieved in P2.7.
- Inspection of the binary PDF files confirmed that HDFCBANK's filings consist of scanned JBIG2 image pages rather than embedded selectable text font tables.
- **Strict Compliance with Safety Rules**:
  - Rather than inventing replacement numbers or unverified values, new linked vintages 26 and 27 were created linking to parent vintages 15 and 16.
  - Vintages 26 and 27 preserve authentic source hashes (`380079d1837a...` and `69c2740c3822...`) but are retained as `verification_status = 'PROVISIONAL'` and `research_eligibility = 'QUARANTINED'`.
  - Vintages 15 and 16 were cleanly marked `SUPERSEDED` by vintages 26 and 27.
  - Zero unverified records have been promoted to `VERIFIED_ELIGIBLE`.

---

## 4. Verification Verdict

- **Phase Status**: `P2.8 IMPLEMENTED & VERIFIED`
- **Scope Safety**: Validated with zero scope-mixing tolerance.
- **Banking Solvency Invariant**: Confirmed ($D/E = \text{NULL}$, customer deposits segregated).
- **HDFC Quarantine**: Fully maintained under authentic provenance.

