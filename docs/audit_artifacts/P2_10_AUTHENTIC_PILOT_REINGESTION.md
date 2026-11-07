# P2.10 — Authentic Pilot Re-Ingestion Report

## 1. Overview & Operational Summary

Phase P2.10 executed the controlled pilot re-ingestion of 10 authentic quarterly filings across the 5 pilot companies:
- **TCS** (Q1 FY25 & Q2 FY25)
- **INFY** (Q1 FY25 & Q2 FY25)
- **RELIANCE** (Q1 FY25 & Q2 FY25)
- **HDFCBANK** (Q1 FY25 & Q2 FY25)
- **ADANIENT** (Q1 FY25 & Q2 FY25)

Target Database: `database/staging_financial_expansion.db`  
Production Database (`database/swing_trading.db`): **Strictly Untouched** (0 writes)

---

## 2. Ingestion Execution & Lineage Audit

Executed via `backend/data_pipeline/execute_authentic_pilot_reingestion.py`.

### Database Progression:
- **Pre-Ingestion Rows**: 17
- **Post-Ingestion Rows**: 27 (+10 new vintages added)
- **Original 17 Records**: 100% preserved (0 deleted, 0 values mutated)

### Complete Ingestion Ledger:

| New ID | Symbol | Quarter | Scope | Ver. Seq. | Parent ID | Verification Status | Research Eligibility | Effective Date | Source NSE Doc Hash |
| :---: | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :--- |
| **18** | TCS | 2024-Q1 | CONSOLIDATED | 2 | 1 | `VERIFIED` | `VERIFIED_ELIGIBLE` | 2024-07-12 | `dc564e8be40a...` |
| **19** | TCS | 2024-Q2 | CONSOLIDATED | 2 | 2 | `VERIFIED` | `VERIFIED_ELIGIBLE` | 2024-10-11 | `fd59a27f69aa...` |
| **20** | INFY | 2024-Q1 | CONSOLIDATED | 2 | 3 | `VERIFIED` | `VERIFIED_ELIGIBLE` | 2024-07-19 | `38afc5e2eac4...` |
| **21** | INFY | 2024-Q2 | CONSOLIDATED | 2 | 4 | `VERIFIED` | `VERIFIED_ELIGIBLE` | 2024-10-18 | `f70b679051e3...` |
| **22** | RELIANCE | 2024-Q1 | CONSOLIDATED | 3 | 11 | `VERIFIED` | `VERIFIED_ELIGIBLE` | 2024-07-22 | `d566e07bebc9...` |
| **23** | RELIANCE | 2024-Q2 | CONSOLIDATED | 3 | 12 | `VERIFIED` | `VERIFIED_ELIGIBLE` | 2024-10-15 | `fbe90e101b1a...` |
| **24** | ADANIENT | 2024-Q1 | CONSOLIDATED | 3 | 13 | `VERIFIED` | `VERIFIED_ELIGIBLE` | 2024-08-01 | `c7ca3e1e2db5...` |
| **25** | ADANIENT | 2024-Q2 | CONSOLIDATED | 3 | 14 | `VERIFIED` | `VERIFIED_ELIGIBLE` | 2024-10-29 | `534e42a8e5da...` |
| **26** | HDFCBANK | 2024-Q1 | CONSOLIDATED | 3 | 15 | `PROVISIONAL` | `QUARANTINED` | 2024-07-22 | `380079d1837a...` |
| **27** | HDFCBANK | 2024-Q2 | CONSOLIDATED | 3 | 16 | `PROVISIONAL` | `QUARANTINED` | 2024-10-21 | `69c2740c3822...` |

---

## 3. Preservation of Safety Rules & Quarantine Integrity

1. **Bidirectional Supersession**:
   - Each previous active vintage was updated with `research_eligibility = 'SUPERSEDED'` and `superseded_by_vintage_id = NEW.id`.
   - Vintages 1, 2, 3, 4, 11, 12, 13, 14, 15, and 16 now accurately point to their respective successors.
2. **Honest Quarantine Handling**:
   - For HDFCBANK, filings were authentically retrieved, but because they comprise scanned document images lacking digital font tables, records 26 and 27 are retained in **`QUARANTINED`** status.
   - They are strictly blocked from being promoted to `VERIFIED_ELIGIBLE`. No synthetic values were manufactured.
3. **Database Integrity**:
   - SQLite triggers `prevent_vintage_deletion` and `prevent_vintage_financial_mutation` continue to enforce zero mutability on historical data.

---

## 4. Verification Verdict

- **Phase Status**: `P2.10 IMPLEMENTED & VERIFIED`
- **Authentic Filings Ingested**: 10
- **Lineage Consistency**: 100% verified across 27 records
- **Quarantine Rigor**: 100% compliant with zero premature promotion

