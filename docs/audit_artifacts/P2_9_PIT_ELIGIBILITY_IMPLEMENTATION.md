# P2.9 — Historical Point-in-Time (PIT) Eligibility & Market Calendar Implementation Report

## 1. Overview & Problem Definition

Financial statement point-in-time (PIT) alignment is essential to prevent look-ahead bias in quantitative research and backtesting. An announcement made after market hours or on non-trading days cannot legally or operationally affect market pricing until the subsequent executable trading session.

Phase P2.9 implements:
1. Deterministic market calendar service based on official NSE/BSE operating hours and trading holidays (2024 & 2025).
2. Point-in-time eligibility query service with strict research status gating.
3. Protected logic engine isolation: Zero modifications to production trading engines.

---

## 2. Market Session Rules & Calendar Implementation

Implemented in `backend/data_pipeline/historical_pit_service.py`:

```
Exchange Operating Hours (Asia/Kolkata):
- Continuous Trading Session: 09:15:00 to 15:30:00 IST
- Market Open Cutoff: 09:00:00 IST
- Market Close Cutoff: 15:30:00 IST
```

### Deterministic Session Mapping:
1. **Pre-Market Announcements (< 09:00:00 IST)**:
   - If publication date is an active trading session $\rightarrow$ **Effective Same Day**.
   - If weekend or holiday $\rightarrow$ **Effective Next Regular Trading Session**.
2. **Continuous Trading Announcements (09:00:00 - 15:30:00 IST)**:
   - If publication date is an active trading session $\rightarrow$ **Effective Same Day**.
   - If non-trading day $\rightarrow$ **Effective Next Regular Trading Session**.
3. **After-Market Announcements (> 15:30:00 IST)**:
   - Always rolls forward $\rightarrow$ **Effective Next Regular Trading Session**.
4. **Weekend Announcements (Saturdays & Sundays)**:
   - Automatically rolls forward past the weekend to the next trading session (typically Monday, or Tuesday if Monday is a holiday).
5. **Exchange Holidays**:
   - Explicitly checks against verified NSE holiday schedule (e.g. Republic Day, Independence Day, Gandhi Jayanti, Diwali, Maharashtra Assembly Elections).
6. **Date-Only Disclosures**:
   - Conservative fallback: Always rolls forward to the next regular trading day to prevent intra-day look-ahead contamination.

---

## 3. Point-in-Time Eligibility Service (`PointInTimeEligibilityService`)

Provides deterministic historical evaluation:
```python
def get_eligible_vintage_as_of(symbol: str, as_of_date: str, filing_scope: str = "CONSOLIDATED") -> Optional[Dict[str, Any]]
```

### Strict Eligibility Invariants:
- `effective_trading_date <= as_of_date`: Future disclosure dates are completely hidden.
- `research_eligibility = 'VERIFIED_ELIGIBLE'`: Only verified records are selected.
- `PROVISIONAL_DEMO`: Blocked from production research and backtesting.
- `QUARANTINED`: Blocked from scoring and trade decisions.
- `SUPERSEDED`: Blocked from current research selection; historical evaluations use whichever vintage was active as of that date.
- Corporate Restatements vs Internal Corrections:
  - Corporate restatement records carry their own publication timestamps and effective dates; they never become visible prior to their own effective date.
  - Internal extraction corrections retain the original effective trading date only when verified against the original authentic source document.

---

## 4. Verification Verdict

- **Phase Status**: `P2.9 IMPLEMENTED & VERIFIED`
- **Exchange Calendar**: 2024–2025 official NSE trading holidays verified.
- **PIT Gating**: Fully enforced via query-level and schema-level constraints.
- **Protected Engines**: 0 edits across all trading logic engines.

