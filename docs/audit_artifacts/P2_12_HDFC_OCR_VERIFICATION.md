# P2.12 — HDFC OCR Verification & Scanned Document Audit Report

## 1. Executive Summary

- **Task**: Inspect HDFC vintages (7, 8, 15, 16, 17, 26, 27), perform OCR/document inspection on authentic source PDFs, verify SHA-256 hashes, and assess whether banking metrics can be reliably extracted or if records must remain quarantined.
- **Auditor Role**: Senior Financial Data Auditor, OCR Engineer, Point-in-Time Data Specialist.
- **Audit Findings**:
  1. All source PDFs in `database/staging_filings_store/HDFCBANK/` are preserved with complete binary integrity.
  2. Authentic NSE filing documents (Announcements 163625 and 165745) were confirmed to be scanned raster images compressed using JBIG2 (`/JBIG2Decode`).
  3. Locally available system inspection confirms zero OCR CLI utilities (`tesseract`, `pdftoppm`) or Python imaging/OCR libraries (`pytesseract`, `pymupdf`, `pypdf`, `PIL`, `cv2`) exist in the environment.
  4. In accordance with Safety Rules ("Never invent missing values. If OCR cannot establish a value reliably, retain NULL and QUARANTINED status. Do not promote records merely because OCR completed successfully"), **HDFCBANK vintages 26 and 27 are strictly retained in `QUARANTINED` status**.
  5. Vintages 7, 8, 15, and 16 remain cleanly `SUPERSEDED`. Vintage 17 remains `PROVISIONAL_DEMO` (standalone).

---

## 2. Source Document Verification & Hash Audit

The authentic filings downloaded directly from official exchange servers were audited against disk binaries:

| Vintage ID | Quarter | Exchange Seq ID | Local Staging File | File Size (Bytes) | SHA-256 Digest | Status |
| :---: | :---: | :---: | :--- | :---: | :--- | :---: |
| **7, 15** | 2024-Q1 | (Pilot Mock) | `HDFCBANK_2024-Q1_b0fa99178e19_HDFCBANK_Q1_FY25_Results.pdf` | 119 | `b0fa99178e19f9472e5299d8a87518c4f1b30dd703bf076643bb2898f0b0f3c1` | `SUPERSEDED` |
| **8, 16, 17** | 2024-Q2 | (Pilot Mock) | `HDFCBANK_2024-Q2_afbb96403d8a_HDFCBANK_Q2_FY25_Results.pdf` | 124 | `afbb96403d8a4bfedeba87bc91bff361773f6a7797f4bb743aed5cae66c6eec9` | `SUPERSEDED` |
| **26** | 2024-Q1 | 163625 | `HDFCBANK_2024-Q1_380079d1837a_NSE_163625.pdf` | 1,126,414 | `380079d1837a08678f629b7ebee3fa216a4a662385aa6dc3100319b13ae3c769` | `AUTHENTIC_EXCHANGE_FILING` |
| **27** | 2024-Q2 | 165745 | `HDFCBANK_2024-Q2_69c2740c3822_NSE_165745.pdf` | 1,366,482 | `69c2740c38221cd3f9b161c36c05b52040dfd1ac279aaf1a778832a7ca9464ce` | `AUTHENTIC_EXCHANGE_FILING` |

---

## 3. PDF Structural & OCR Inspection

A binary parse of `HDFCBANK_2024-Q1_380079d1837a_NSE_163625.pdf` and `HDFCBANK_2024-Q2_69c2740c3822_NSE_165745.pdf` revealed:
- **Pages**: 14 (Q1) and 23 (Q2).
- **Embedded Images**: 14 (Q1) and 23 (Q2).
- **Compression**: All financial tables are embedded as JBIG2-compressed raster scans (`/JBIG2Decode`).
- **Font Descriptors**: 0 font descriptors, 0 `/ToUnicode` character mappings.
- **Embedded Text Stream**: Only metadata signatures ("Digitally signed by SRINIVASA RANGAN VEDANTHACHARI") contain digital glyphs. All tabular accounting line items are purely graphical pixels.

### Environment Tooling Audit:
A scan of system executables and Python packages identified:
- Tesseract OCR CLI: **Not installed** (`tesseract` not found on `PATH`).
- Poppler utilities (`pdftoppm`, `pdfimages`): **Not installed**.
- Imaging / OCR Python packages (`pytesseract`, `pymupdf`, `pypdf`, `PIL`, `cv2`): **Not installed**.

Per prompt instructions ("If additional software is required, identify it before installing anything"), we explicitly identify the missing prerequisites rather than performing uncoordinated global installations:
- Prerequisite: `tesseract-ocr` binary package + `pytesseract` + `pymupdf` or `pdf2image`.

---

## 4. Financial Metric Verification Ledger (HDFCBANK)

| Metric | Target Scope | V26/V27 Staging Value | OCR / Document Result | Source Page | Verification Result | Confidence / Uncertainty |
| :--- | :--- | :---: | :---: | :---: | :---: | :--- |
| **Total Income (Q1)** | CONSOLIDATED | ₹83,701.0 Cr | Scanned Image | Pg 3 | **UNCONFIRMED** | High uncertainty; scanned pixels unparsed |
| **Net Profit (PAT) (Q1)** | CONSOLIDATED | ₹16,474.0 Cr | Scanned Image | Pg 3 | **UNCONFIRMED** | High uncertainty; scanned pixels unparsed |
| **EPS (Q1)** | CONSOLIDATED | 21.65 | Scanned Image | Pg 3 | **UNCONFIRMED** | High uncertainty; scanned pixels unparsed |
| **NII (Q1)** | CONSOLIDATED | ₹29,837.0 Cr | Scanned Image | Pg 2 | **UNCONFIRMED** | In standalone press release; unconfirmed in consolidated scan |
| **Customer Deposits (Q1)** | CONSOLIDATED | ₹23,79,100.0 Cr | Scanned Image | Pg 5 | **UNCONFIRMED** | High uncertainty; scanned pixels unparsed |
| **CRAR (CAR) (Q1)** | CONSOLIDATED | 19.33% | Scanned Image | Pg 4 | **UNCONFIRMED** | High uncertainty; scanned pixels unparsed |
| **Gross NPA (%) (Q1)** | CONSOLIDATED | 1.33% | Scanned Image | Pg 4 | **UNCONFIRMED** | High uncertainty; scanned pixels unparsed |
| **Net NPA (%) (Q1)** | CONSOLIDATED | 0.39% | Scanned Image | Pg 4 | **UNCONFIRMED** | High uncertainty; scanned pixels unparsed |
| **Total Income (Q2)** | CONSOLIDATED | ₹121,457.0 Cr | Scanned Image | Pg 5 | **UNCONFIRMED** | High uncertainty; scanned pixels unparsed |
| **Net Profit (PAT) (Q2)** | CONSOLIDATED | ₹17,830.0 Cr | Scanned Image | Pg 5 | **UNCONFIRMED** | High uncertainty; scanned pixels unparsed |
| **EPS (Q2)** | CONSOLIDATED | 23.40 | Scanned Image | Pg 5 | **UNCONFIRMED** | High uncertainty; scanned pixels unparsed |
| **Corporate D/E** | CONSOLIDATED | `NULL` | Invariant | N/A | **VERIFIED NULL** | Compliant with banking solvency rules |
| **ROCE** | CONSOLIDATED | `NULL` | Invariant | N/A | **VERIFIED NULL** | Compliant with banking solvency rules |

---

## 5. Scope-Safety & Invariant Audit

1. **Standalone vs Consolidated Separation**:
   - Vintages 7 and 15 erroneously contained standalone top-line numbers labeled as consolidated.
   - Vintages 26 and 27 isolate the authentic exchange PDF URLs, but because digital extraction is unconfirmed, **no data promotion has occurred**.
   - Standalone banking metrics are strictly barred from contaminating consolidated records.
2. **Quarantine Retention**:
   - Vintages 26 and 27 remain flagged:
     - `verification_status = 'PROVISIONAL'`
     - `research_eligibility = 'QUARANTINED'`
   - Point-in-Time queries for HDFCBANK evaluate to `None`, successfully shielding all downstream financial scoring and backtesting pipelines from unverified data.

