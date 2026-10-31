# Remediation Plan: Swing Trading Intelligence Platform

## Priority 1: High Priority (Quality & Resilience)
*None.* All 478 backend unit/integration tests, 51 audit tests, and 288 frontend unit tests pass without regression. Zero critical accounting, security, or data corruption bugs were found.

---

## Priority 2: Medium Priority (Data Completeness)

### REM-001: Populate `publication_date` in `quarterly_results` Table (Relates to DEF-003)
* **Root Cause:** Database table `quarterly_results` currently has `NULL` for `publication_date` across all 260 rows.
* **Current Safeguard:** AUDIT-001 conservative fallback correctly applies:
  $$\text{Availability Timestamp} = \text{Quarter End Date} + 45\text{ days}$$
  This prevents lookahead contamination.
* **Proposed Remediation:** Implement an automated scraper or vendor feed script to populate actual NSE/BSE corporate filing timestamps.
* **Risk of Regression:** Extremely low if integrated via existing `financial_service.py` ingestion pipeline.

---

## Priority 3: Low Priority (API Contract Tightening)

### REM-002: Return Explicit 404 on Unknown Stock Symbols (Relates to DEF-001)
* **Root Cause:** `/api/stocks/{symbol}` in `backend/app.py` constructs a full response payload with `status: INSUFFICIENT` for unknown symbols instead of throwing `HTTPException(status_code=404)`.
* **Proposed Remediation:**
  ```python
  company = get_company_classification(symbol_clean)
  if not company or not company.get("symbol"):
      raise HTTPException(status_code=404, detail=f"Stock symbol '{symbol_clean}' not found.")
  ```
* **Risk of Regression:** Requires checking if frontend `StockDetail.jsx` depends on the `status: INSUFFICIENT` dictionary or handles 404 natively.

### REM-003: Validate `timeframe` Query Parameter (Relates to DEF-002)
* **Root Cause:** `/api/stocks/{symbol}/history` allows any string for `timeframe` and falls back silently to all candles.
* **Proposed Remediation:** Enforce `timeframe: Literal["1M", "3M", "6M", "1Y", "ALL"] = "1M"` in FastAPI router.
* **Risk of Regression:** Very low.

---

## Priority 4: Informational (Frontend Build Optimization)

### REM-004: Standardize Dynamic Import in `Sidebar.jsx` (Relates to DEF-004)
* **Proposed Remediation:** Replace dynamic `import('../services/api.js')` with top-level static import in `Sidebar.jsx`.
* **Risk of Regression:** None.

