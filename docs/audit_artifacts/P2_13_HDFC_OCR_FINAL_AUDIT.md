# P2.13 Audit Artifact: HDFC Bank OCR & Scanned Binary Verification Final Audit

**Audit Date**: 2026-11-06  
**Auditor**: Senior Financial Data Auditor, OCR Engineer & Point-in-Time Data Specialist  
**Target Entities**: HDFC Bank Limited (`HDFCBANK`, Company ID 5)  
**Target Vintages**: 7, 8, 15, 16, 17, 26, 27  
**Status**: VERIFICATION GAPS REMAIN — SCAN RASTER BINARIES QUARANTINED  

---

## 1. Executive Summary

Phase P2.12 and P2.13 evaluated the capability of extracting and independently verifying commercial banking metrics for HDFC Bank Limited (`HDFCBANK`) across Q1 FY25 and Q2 FY25.

Audit findings:
1. **Source Binary Type**: The official exchange filings retrieved from the National Stock Exchange (`NSE 163625` and `NSE 165745`) are **pure scanned raster PDF images** using `JBIG2Decode` image compression. They contain zero embedded digital text streams.
2. **Execution Environment Audit**: An exhaustive inspection of the runtime environment demonstrated that all standard optical character recognition (OCR) and PDF rasterization tools (`tesseract`, `poppler`, `pdftoppm`, `pdfimages`, `pytesseract`, `fitz` / `PyMuPDF`, `pypdf`, `pdf2image`, `PIL`, `cv2`) are **absent** from the host environment.
3. **Audit Invariant Enforcement**: In strict compliance with the anti-hallucination mandate (*"Never invent missing values. If OCR cannot establish a value reliably, retain NULL and QUARANTINED status. Do not promote records merely because OCR completed successfully."*), no synthetic values were fabricated.
4. **Current Status**: All HDFC Bank consolidated financial vintages (vintages 26 and 27) remain strictly locked in **`QUARANTINED`** status and blocked from research eligibility.

---

## 2. Inventory of HDFC Bank Vintages

| Vintage ID | Quarter | Scope | Version | Revision Type | Verification Status | Research Eligibility | Superseded By | Audit Decision |
| :---: | :---: | :---: | :---: | :--- | :--- | :--- | :---: | :--- |
| **7** | 2024-Q1 | CONSOLIDATED | 1 | INITIAL_INGESTION | REJECTED | SUPERSEDED | 15 | Archived legacy pilot mock record |
| **8** | 2024-Q2 | CONSOLIDATED | 1 | INITIAL_INGESTION | REJECTED | SUPERSEDED | 16 | Archived legacy pilot mock record |
| **15** | 2024-Q1 | CONSOLIDATED | 2 | SCOPE_REALIGNMENT | REJECTED | SUPERSEDED | 26 | Archived P2.5 remediation record |
| **16** | 2024-Q2 | CONSOLIDATED | 2 | SCOPE_REALIGNMENT | REJECTED | SUPERSEDED | 27 | Archived P2.5 remediation record |
| **17** | 2024-Q2 | STANDALONE | 1 | INITIAL_INGESTION | PROVISIONAL | PROVISIONAL_DEMO | NULL | Standalone banking pilot record (blocked from consolidated research) |
| **26** | 2024-Q1 | CONSOLIDATED | 3 | INITIAL_INGESTION | PROVISIONAL | **QUARANTINED** | NULL | **RETAINED IN QUARANTINE** pending OCR environment |
| **27** | 2024-Q2 | CONSOLIDATED | 3 | INITIAL_INGESTION | PROVISIONAL | **QUARANTINED** | NULL | **RETAINED IN QUARANTINE** pending OCR environment |

---

## 3. Host Environment Tooling Audit

A programmatic audit of system binaries and Python libraries was executed on the host runtime:

```python
# System Tooling Audit
which tesseract      -> NOT FOUND
which pdftoppm       -> NOT FOUND (poppler-utils absent)
which pdfimages      -> NOT FOUND
which jbig2dec       -> NOT FOUND
which gs             -> NOT FOUND (Ghostscript absent)

# Python Package Audit
import pytesseract   -> ModuleNotFoundError
import fitz (PyMuPDF)-> ModuleNotFoundError
import pypdf         -> ModuleNotFoundError
import pdf2image     -> ModuleNotFoundError
import PIL (Pillow)  -> ModuleNotFoundError
import cv2 (OpenCV)  -> ModuleNotFoundError
```

### Technical Root Cause
The operating system environment is a minimal Windows execution container lacking image manipulation DLLs, Ghostscript, Poppler binaries, and Tesseract OCR language packs. Attempting to decompress `JBIG2` image bitstreams without `jbig2dec` or `PyMuPDF` results in binary decoding failure.

---

## 4. Source Document Binary Inspection

Both authentic filings stored in `database/staging_filings_store/HDFCBANK/` were independently inspected:

### 1. Q1 FY25 Filing
- **Filename**: `HDFCBANK_2024-Q1_b0fa99178e19_HDFCBANK_Q1_FY25_Results.pdf`
- **Announcement ID**: `NSE 163625`
- **Exchange Broadcast Timestamp**: `2024-07-20 14:15:17 IST`
- **Effective Trading Date**: `2024-07-22`
- **SHA-256 Fingerprint**: `380079d1837a08678f629b7ebee3fa216a4a662385aa6dc3100319b13ae3c769`
- **Binary Structure**: Scanned physical paper disclosure, compressed via JBIG2 stream objects. Zero extractable ASCII/Unicode glyphs.

### 2. Q2 FY25 Filing
- **Filename**: `HDFCBANK_2024-Q2_11feff336f34_HDFCBANK_Q2_FY25_Results.pdf`
- **Announcement ID**: `NSE 165745`
- **Exchange Broadcast Timestamp**: `2024-10-19 14:12:47 IST`
- **Effective Trading Date**: `2024-10-21`
- **SHA-256 Fingerprint**: `69c2740c38221cd3f9b161c36c05b52040dfd1ac279aaf1a778832a7ca9464ce`
- **Binary Structure**: Scanned physical paper disclosure, compressed via JBIG2 stream objects. Zero extractable ASCII/Unicode glyphs.

---

## 5. Integrity & Safety Invariant Enforcement

To protect downstream production systems, the following strict controls are enforced:

1. **Anti-Hallucination Gate**: Under no circumstances will the data pipeline invent or guess missing numbers for HDFC Bank (e.g. Net Interest Income, Gross NPA, Net NPA, NIM, Customer Deposits, Total Income).
2. **Scope Isolation**: Standalone metrics from Vintage 17 are strictly prohibited from being copied into Consolidated records (vintages 26 and 27).
3. **Database Quarantine**: Vintages 26 and 27 have `research_eligibility = 'QUARANTINED'` and `verification_status = 'PROVISIONAL'`.
4. **Point-in-Time Service Fail-Closed**: `PointInTimeEligibilityService.get_eligible_vintage_as_of("HDFCBANK", ...)` explicitly filters out any records with `research_eligibility = 'QUARANTINED'`. As a result, 0 records are returned, preventing erroneous backtest trades.

---

## 6. Prerequisite Steps for Subsequent OCR Unlocking

To transition HDFC Bank records from `QUARANTINED` to `VERIFIED_ELIGIBLE`, the following platform components must be provisioned:

1. **System OCR Engine**:
   - Install Tesseract OCR (`tesseract-ocr-w64-v5.x.exe`) with English trained data (`eng.traineddata`).
   - Add Tesseract installation path to system `PATH`.
2. **PDF Rasterizer**:
   - Install Poppler for Windows (`poppler-24.x`) or PyMuPDF (`pip install pymupdf`).
3. **Python Bridge**:
   - Install `pytesseract` and `pillow`.
4. **Independent Dual Verification**:
   - Run two independent OCR passes with character-level confidence scores > 95%.
   - Validate extracted banking metrics against the mathematical balance sheet identity:
     $$\text{Total Assets} = \text{Total Liabilities and Capital}$$

---

## 7. Audit Conclusion

HDFC Bank's authentic filing binaries are preserved with 100% cryptographic integrity. Due to the absence of local OCR rasterization infrastructure, the records remain correctly quarantined. Downstream backtesting and signal generation engines are completely insulated from unverified banking data.

