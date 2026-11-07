# P2.6 — Classification and Financial Vintage Lineage Schema Implementation Report

## 1. Executive Summary & Verification Verdict

| Audit & Governance Dimension | Recorded Status | Assessment |
| :--- | :--- | :---: |
| **Milestone** | Phase P2.6 — Classification & Financial Vintage Lineage Schema | **IMPLEMENTED** |
| **Approved Architecture Baseline** | `docs/audit_artifacts/P2_5_5_IMPLEMENTATION_READINESS_REVIEW.md` | **COMPLIANT** |
| **Target Database** | `database/staging_financial_expansion.db` | **CONFIRMED** |
| **Production Database (`database/swing_trading.db`)** | Hash: `1a2036fcc72af59b3633b5c2a077c26dd45756b3360824f36e995e2e805a28a8` (260 rows) | **UNTOUCHED (0 writes)** |
| **Staging Pre-Migration Hash** | `6ea5a58bce4accd276255794b8e2001c68adeedb79daf2804d1d16a94f698e7b` (17 rows) | **RECORDED** |
| **Staging Post-Migration Hash** | `fa6b42c37ca02bd7c253af613e4f86c601c06b99b91608dae080538f86a550ab` (17 rows) | **VERIFIED** |
| **Classification Dimensions** | 4 orthogonal dimensions implemented with SQLite CHECK constraints | **ACTIVE** |
| **Timestamp Model** | 5 canonical timestamps enforced; published_at immutable | **ACTIVE** |
| **Lineage & Supersession** | Bidirectional lineage implemented; self/circular lineage blocked | **ACTIVE** |
| **Existing Records Migrated** | All 17 staging records preserved (0 deleted, 0 values mutated) | **100% PRESERVED** |
| **Protected Engine Files** | `strategy_engine.py`, `signal_engine.py`, `trade_quality_engine.py`, `portfolio_simulator.py` | **UNTOUCHED (0 edits)** |
| **Git Operations** | Zero git commits, zero git pushes | **CLEAN** |
| **Unit Test Suite** | 33 passed across 4 test suites (isolated temporary SQLite DB fixtures) | **100% PASS** |
| **Final Phase Verdict** | **`P2.6 COMPLETE — STAGING SCHEMA VERIFIED`** | — |

---

## 2. Baseline Database Hashes & Row Counts

Before executing any migrations or code modifications, baseline integrity was audited:

```
┌──────────────────────────────────────────────────────────────────────────────────────────────────┐
│                               DATABASE INTEGRITY COMPARISON                                      │
├───────────────────────────────┬───────────────────────────────────────────┬──────────┬───────────┤
│ Target Environment            │ SHA-256 Digest                            │ Pre Rows │ Post Rows │
├───────────────────────────────┼───────────────────────────────────────────┼──────────┼───────────┤
│ Production: swing_trading.db  │ 1a2036fcc72af59b3633b5c2a077c26dd45756b3...│ 260      │ 260 (0 Δ) │
│ Staging: staging_financial... │ fa6b42c37ca02bd7c253af613e4f86c601c06b99...│ 17       │ 17 (0 Δ)  │
└───────────────────────────────┴───────────────────────────────────────────┴──────────┴───────────┘
```

Safety constraints strictly enforced:
- Zero write attempts on `database/swing_trading.db`.
- Legacy `quarterly_results` table remains 100% intact.
- Migration and repository scripts enforce hardcoded runtime exceptions if directed at `database/swing_trading.db`.

---

## 3. Classification Dimensions & Invariant Schema

The schema migration creates four independent, orthogonal classification dimensions in `quarterly_financial_vintages`:

```
                               ┌───────────────────────────────────────────────┐
                               │       FOUR INDEPENDENT DIMENSIONS (P2.6)      │
                               └───────────────────────────────────────────────┘
                                                       │
         ┌───────────────────────────┬─────────────────┴─────────┬───────────────────────────┐
         ▼                           ▼                           ▼                           ▼
┌──────────────────┐       ┌──────────────────┐        ┌──────────────────┐        ┌──────────────────┐
│company_filing_type       │internal_revision_│        │verification_     │        │research_         │
│                  │       │type              │        │status            │        │eligibility       │
├──────────────────┤       ├──────────────────┤        ├──────────────────┤        ├──────────────────┤
│• ORIGINAL        │       │• INITIAL_        │        │• VERIFIED        │        │• VERIFIED_       │
│• REVISED_        │       │  INGESTION       │        │• PROVISIONAL     │        │  ELIGIBLE        │
│  DISCLOSURE      │       │• EXTRACTION_     │        │• REJECTED        │        │• PROVISIONAL_    │
│• CORPORATE_      │       │  CORRECTION      │        └──────────────────┘        │  DEMO            │
│  RESTATEMENT     │       │• SCOPE_          │                                    │• QUARANTINED     │
│• ANNUAL_AUDITED_ │       │  REALIGNMENT     │                                    │• SUPERSEDED      │
│  FINAL           │       │• SECTOR_         │                                    └──────────────────┘
└──────────────────┘       │  NORMALIZATION   │
                           └──────────────────┘
```

### Invariant Rules & SQLite Constraints

1. **Semantic Conflation Prevention (`prevent_extraction_restatement_conflation` trigger):**
   Internal pipeline corrections (`EXTRACTION_CORRECTION`, `SCOPE_REALIGNMENT`, `SECTOR_NORMALIZATION`) are strictly prohibited from populating `company_filing_type = 'CORPORATE_RESTATEMENT'`.
2. **Promotion Gating:**
   A record cannot have `research_eligibility = 'VERIFIED_ELIGIBLE'` unless `verification_status = 'VERIFIED'`. Attempting to insert or promote an unverified or provisional record to `VERIFIED_ELIGIBLE` raises an immediate `Integrity Error`.
3. **Banking Neutral Solvency (`CHECK(is_banking_institution = 0 OR debt_equity IS NULL)`):**
   Commercial banks and financial institutions have corporate Debt-to-Equity ($D/E$) and ROCE enforced to `NULL`. Customer deposits are segregated from borrowings.

---

## 4. Canonical Timestamp Model

The schema implements the canonical 5-timestamp tracking model:

| Column | Type | Nullable | Semantics | Immutability Rule |
| :--- | :--- | :---: | :--- | :--- |
| `published_at` | `TEXT` (ISO 8601) | **NO** | Exact date and time when the disclosure was broadcast by the exchange. | **Strictly immutable via trigger.** |
| `effective_trading_date` | `TEXT` (`YYYY-MM-DD`) | **NO** | First executable market trading session where the market could act on the filing. | **Strictly immutable via trigger.** |
| `ingested_at` | `TEXT` (ISO 8601) | YES | Timestamp when our pipeline initially ingested the document artifact. | Set on record creation. |
| `internally_corrected_at`| `TEXT` (ISO 8601) | YES | Timestamp when an internal correction vintage was generated. | Populated only on internal revisions. |
| `company_revision_published_at` | `TEXT` (ISO 8601) | YES | Publication timestamp of later corporate revision or restatement. | Independent of initial publication. |

---

## 5. Lineage & Supersession Semantics

Lineage columns enable complete bidirectional graph traversal across vintages:

```
       [Vintage 5: Reliance Q1 Initial] ──superseded_by──► [Vintage 11: Reliance Q1 Remediated]
              (SUPERSEDED)                                       (PROVISIONAL_DEMO)
              parent_vintage_id: NULL                            parent_vintage_id: 5
              supersedes_vintage_id: NULL                        supersedes_vintage_id: 5
```

- **`parent_vintage_id`**: Direct predecessor in the data pipeline tree.
- **`supersedes_vintage_id`**: Earlier version of the same disclosure replaced by this record.
- **`superseded_by_vintage_id`**: Successor vintage that replaces this record.
- **`revision_reason`**: Human/auditor rationale for the revision.
- **`revision_source`**: Submitting entity or pipeline module.
- **Anti-Self-Supersession:** SQLite CHECK constraints `CHECK(superseded_by_vintage_id != id)` and trigger guards block self-referential links.
- **Anti-Circular Lineage:** SQLite trigger `prevent_vintage_financial_mutation` aborts any update where `superseded_by_vintage_id = OLD.supersedes_vintage_id`.

---

## 6. Migration Mapping for Existing 17 Vintages

All 17 existing records in `database/staging_financial_expansion.db` were preserved with zero financial data alteration:

| ID | Company | Quarter | Filing Scope | `company_filing_type` | `internal_revision_type` | `verification_status` | `research_eligibility` | Rationale |
| :---: | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :--- |
| **1** | TCS | 2024-Q1 | CONSOLIDATED | `ORIGINAL` | `INITIAL_INGESTION` | `PROVISIONAL` | `PROVISIONAL_DEMO` | Mock test fixture; unverified |
| **2** | TCS | 2024-Q2 | CONSOLIDATED | `ORIGINAL` | `INITIAL_INGESTION` | `PROVISIONAL` | `PROVISIONAL_DEMO` | Mock test fixture; unverified |
| **3** | INFY | 2024-Q1 | CONSOLIDATED | `ORIGINAL` | `INITIAL_INGESTION` | `PROVISIONAL` | `PROVISIONAL_DEMO` | Mock test fixture; unverified |
| **4** | INFY | 2024-Q2 | CONSOLIDATED | `ORIGINAL` | `INITIAL_INGESTION` | `PROVISIONAL` | `PROVISIONAL_DEMO` | Mock test fixture; unverified |
| **5** | RELIANCE | 2024-Q1 | CONSOLIDATED | `ORIGINAL` | `INITIAL_INGESTION` | `REJECTED` | `SUPERSEDED` | Flawed gross turnover; replaced by 11 |
| **6** | RELIANCE | 2024-Q2 | CONSOLIDATED | `ORIGINAL` | `INITIAL_INGESTION` | `REJECTED` | `SUPERSEDED` | Flawed gross turnover; replaced by 12 |
| **7** | HDFCBANK | 2024-Q1 | CONSOLIDATED | `ORIGINAL` | `INITIAL_INGESTION` | `REJECTED` | `SUPERSEDED` | Flawed bank debt/equity; replaced by 15 |
| **8** | HDFCBANK | 2024-Q2 | CONSOLIDATED | `ORIGINAL` | `INITIAL_INGESTION` | `REJECTED` | `SUPERSEDED` | Flawed bank debt/equity; replaced by 16 |
| **9** | ADANIENT | 2024-Q1 | CONSOLIDATED | `ORIGINAL` | `INITIAL_INGESTION` | `REJECTED` | `SUPERSEDED` | Flawed other income; replaced by 13 |
| **10** | ADANIENT | 2024-Q2 | CONSOLIDATED | `ORIGINAL` | `INITIAL_INGESTION` | `REJECTED` | `SUPERSEDED` | Flawed other income; replaced by 14 |
| **11** | RELIANCE | 2024-Q1 | CONSOLIDATED | `ORIGINAL` | `EXTRACTION_CORRECTION`| `PROVISIONAL` | `PROVISIONAL_DEMO` | Net Revenue ₹236,217 Cr normalized |
| **12** | RELIANCE | 2024-Q2 | CONSOLIDATED | `ORIGINAL` | `EXTRACTION_CORRECTION`| `PROVISIONAL` | `PROVISIONAL_DEMO` | Net Revenue ₹235,481 Cr normalized |
| **13** | ADANIENT | 2024-Q1 | CONSOLIDATED | `ORIGINAL` | `EXTRACTION_CORRECTION`| `PROVISIONAL` | `PROVISIONAL_DEMO` | Net Revenue ₹25,472.40 Cr normalized |
| **14** | ADANIENT | 2024-Q2 | CONSOLIDATED | `ORIGINAL` | `EXTRACTION_CORRECTION`| `PROVISIONAL` | `PROVISIONAL_DEMO` | Net Revenue ₹22,608.0 Cr normalized |
| **15** | HDFCBANK | 2024-Q1 | CONSOLIDATED | `ORIGINAL` | `SCOPE_REALIGNMENT` | `REJECTED` | `QUARANTINED` | Defect: retains standalone top-line |
| **16** | HDFCBANK | 2024-Q2 | CONSOLIDATED | `ORIGINAL` | `SCOPE_REALIGNMENT` | `REJECTED` | `QUARANTINED` | Defect: copies standalone NII/NPA |
| **17** | HDFCBANK | 2024-Q2 | STANDALONE | `ORIGINAL` | `INITIAL_INGESTION` | `PROVISIONAL` | `PROVISIONAL_DEMO` | Standalone banking disclosure isolated |

---

## 7. Service Layer Enhancements

`backend/data_pipeline/staging_financial_vintage_service.py` was extended with the following transactional, auditable methods:

1. `create_internal_correction(predecessor_id, corrected_data, revision_type, reason, auditor_id)`:
   Transactionally inserts a corrected vintage (incrementing `version_sequence`), populates `internally_corrected_at`, links parent/supersedes IDs, and marks the predecessor `superseded_by_vintage_id = new_id` and `research_eligibility = 'SUPERSEDED'`.
2. `link_company_revision(predecessor_id, revision_data, company_filing_type, reason)`:
   Transactionally inserts a corporate restatement or revised disclosure, maintains separate publication timestamps, and links supersession.
3. `quarantine_vintage(vintage_id, reason, auditor_id)`:
   Transitions `research_eligibility` to `QUARANTINED` and appends an auditable note.
4. `record_status_transition(vintage_id, new_verification_status, new_research_eligibility, notes)`:
   Validates invariant constraints (promotion to `VERIFIED_ELIGIBLE` requires `verification_status = 'VERIFIED'`) and updates status.
5. `get_vintage_lineage(vintage_id)`:
   Traverses ancestors and successors to return complete audit tree.
6. `get_point_in_time_vintages(symbol, evaluation_date, filing_scope, allow_provisional, include_quarantined)`:
   Ranks active vintages strictly before `effective_trading_date <= evaluation_date`. Excludes `QUARANTINED` and `REJECTED` records.

---

## 8. Verification & Test Suite Execution

The test suite runs against isolated temporary SQLite databases (`tmp_path`) and confirms schema invariants and migration fidelity:

```
============================= test session starts =============================
platform win32 -- Python 3.14.7, pytest-9.1.1, pluggy-1.7.0
rootdir: C:\Users\vigne\OneDrive\Desktop\projects\swing-trading-tool
plugins: anyio-4.15.1, platformdirs-4.13.5
collected 33 items

backend\tests\test_p2_staging_financial_vintage.py ..........            [ 30%]
backend\tests\test_p2_financial_ingestion_pilot.py ......                [ 48%]
backend\tests\test_p2_pilot_remediation.py ......                        [ 66%]
backend\tests\test_p2_6_schema_lineage.py ...........                    [100%]

============================= 33 passed in 2.92s ==============================
```

Test coverage includes:
- [x] All 4 classification dimensions accept valid values.
- [x] Invalid values rejected by SQLite CHECK constraints.
- [x] Semantic conflation of internal fixes with corporate restatements rejected.
- [x] Promotion to `VERIFIED_ELIGIBLE` blocked without `verification_status = 'VERIFIED'`.
- [x] `published_at` and financial figures immutable via triggers.
- [x] Bidirectional parent-child and supersedes lineage created transactionally.
- [x] Self-supersession and circular lineage rejected.
- [x] Quarantined records blocked from point-in-time retrieval.
- [x] Migration fidelity verified against copy of staging database: 17 records preserved, HDFC 15 & 16 quarantined.

---

## 9. Known Limitations & Next Steps

1. **Document Retrieval Engine (Phase P2.7):**
   The 17 records currently in staging remain `PROVISIONAL_DEMO` or `QUARANTINED` because genuine binary PDF exchange filings have not yet been downloaded. Phase P2.7 will implement the dual-mode exchange retrieval pipeline.
2. **Scope-Aware Parser (Phase P2.8):**
   HDFC Bank consolidated vintages (15 & 16) remain `QUARANTINED` until the Phase P2.8 scope-safe parser processes separate Standalone and Consolidated statements directly from genuine PDF filings.
3. **PIT Calendar & Session Timing (Phase P2.9):**
   The current schema stores `published_at` and `effective_trading_date`. Full market-session cutoff logic (15:30 IST) and NSE trading holiday integration will be formalized in Phase P2.9.

---

## 10. Rollback Strategy

If rollback of Phase P2.6 staging schema is ever required:
1. Restore pre-migration staging backup:
   `cp database/staging_financial_expansion.db.backup database/staging_financial_expansion.db`
2. No rollback is necessary for `database/swing_trading.db` as it was never touched or modified.

---

## 11. Final Phase Sign-Off Verdict

**`P2.6 COMPLETE — STAGING SCHEMA VERIFIED`**
- Staging database schema evolved with 4D classification, 5 canonical timestamps, and complete lineage tracking.
- All 17 existing staging records preserved and classified under conservative audit rules.
- Production database remained untouched with unchanged SHA-256 hash.
- Zero modifications to protected strategy or signal engines.
- Ready for Phase P2.7 (Authentic Document Retrieval & Verification Engine).

