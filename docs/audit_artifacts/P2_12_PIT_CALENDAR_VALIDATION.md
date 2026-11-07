# P2.12 — Point-in-Time (PIT) Calendar & Market Hours Validation Report

## 1. Overview & Evaluation Scope

Point-in-Time (PIT) financial data integrity requires strict temporal boundaries to prevent look-ahead bias in algorithmic models and backtests. This audit evaluates:
1. Exact verified trading calendar coverage.
2. Market session hours and announcement timestamp mapping.
3. Holiday and weekend boundary handling.
4. Fail-closed behavior for unverified calendar ranges.
5. Invariant handling of corporate restatements and internal extraction corrections.

---

## 2. Calendar Coverage Audit & Fail-Closed Enforcement

The market calendar service is implemented in `backend/data_pipeline/historical_pit_service.py`.

### Verified Holiday Coverage:
- **2024 Coverage**: Exactly 17 official NSE trading holidays (Republic Day, Mahashivratri, Holi, Good Friday, Id-Ul-Fitr, Ram Navami, Maharashtra Day, General Parliamentary Elections, Bakri Id, Muharram, Independence Day, Gandhi Jayanti, Diwali Laxmi Pujan, Gurunanak Jayanti, Maharashtra Assembly Elections, Christmas).
- **2025 Coverage**: Exactly 14 official NSE trading holidays (Mahashivratri, Holi, Id-Ul-Fitr, Mahavir Jayanti, Ambedkar Jayanti, Good Friday, Maharashtra Day, Independence Day, Ganesh Chaturthi, Gandhi Jayanti / Dussehra, Diwali, Diwali Balipratipada, Prakash Gurpurb, Christmas).
- **2026+ Coverage**: **0 verified holidays loaded**.

### Fail-Closed Principle:
- Crucial Audit Finding: The system **must fail closed** when an evaluation date falls outside the verified calendar window.
- Treating unverified dates as regular trading sessions when holiday data is missing would introduce false assumptions.
- An explicit validation check verifies calendar coverage before returning trading day calculations.

---

## 3. Market Session Timestamp Rules Validation

The deterministic cutoff engine was tested against verified empirical cases:

| Scenario Type | Input Announcement Timestamp | Market Operating Context | Expected Effective Trading Date | Evaluated Date | Result |
| :--- | :--- | :--- | :---: | :---: | :---: |
| **Intraday Market Session** | `2024-10-29 14:58:48` | Tuesday 14:58 IST (< 15:30 close) | `2024-10-29` | `2024-10-29` | **PASS** |
| **After-Market Close** | `2024-07-11 15:38:49` | Thursday 15:38 IST (> 15:30 close) | `2024-07-12` | `2024-07-12` | **PASS** |
| **After-Market Friday** | `2024-07-19 19:16:04` | Friday 19:16 IST (> 15:30 close) | `2024-07-22` (Monday) | `2024-07-22` | **PASS** |
| **Weekend Board Meeting** | `2024-07-20 14:15:17` | Saturday 14:15 IST (Non-trading) | `2024-07-22` (Monday) | `2024-07-22` | **PASS** |
| **Pre-Market Announcement** | `2024-07-19 08:30:00` | Friday 08:30 IST (< 09:00 open) | `2024-07-19` | `2024-07-19` | **PASS** |
| **Missing Time (Date-Only)** | `2024-07-11` | Ambiguous publication time | `2024-07-12` (Next Day) | `2024-07-12` | **PASS** |

---

## 4. Corporate Restatements vs Internal Corrections

The PIT service strictly differentiates restatements from extraction fixes:

1. **Genuine Corporate Restatement**:
   - Company files a restated disclosure months or years after original results.
   - Restatement carries its own new `published_at` and `effective_trading_date`.
   - **Audit Verification**: A backtest evaluating a portfolio on a date prior to the restatement's effective date receives the original active vintage. The restatement is completely invisible until its own effective date.
2. **Internal Extraction Correction**:
   - An internal bug in the parsing pipeline is fixed (e.g. unit scale, scope alignment).
   - The corrected record retains the original disclosure's `published_at` and `effective_trading_date` only when verified against the original authentic filing.
   - Internal correction records are strictly prohibited from populating `company_filing_type = 'CORPORATE_RESTATEMENT'`.

---

## 5. Research Gating & Visibility Validation

Verification query rules in `PointInTimeEligibilityService`:
- `VERIFIED_ELIGIBLE`: Visible only on or after `effective_trading_date`.
- `PROVISIONAL_DEMO`: Blocked (returns `None`).
- `QUARANTINED`: Blocked (returns `None`).
- `SUPERSEDED`: Excluded from current selection; point-in-time timeline tracks historical validity.

