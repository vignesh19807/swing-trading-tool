# PHASE 3.2 — CLOUD CI PORTABILITY AND TEST ISOLATION REPORT
**Swing Trading Intelligence Platform**  
**Audit & Implementation Date:** March 2026 / Turn Baseline  
**Auditor & Implementation Specialist:** Senior DevOps Engineer, Software Reliability Engineer & Financial Data Auditor  
**Classification:** Cloud CI Infrastructure, Test Suite Portability & Data Governance Isolation  

---

## EXECUTIVE SUMMARY

Phase 3.2 resolved the cloud runner portability blocker identified in Phase 3.1. The repository root excludes `database/*.db` via `.gitignore`, preventing the 9.0 MB production financial database (`database/swing_trading.db`) and the 5.3 MB staging database (`database/staging_financial_expansion.db`) from being checked into Git. Consequently, pristine GitHub Actions cloud runners checking out the repository lacked the physical database files required by historical governance audit suites.

Phase 3.2 established a formal, cryptographically sound test architecture that segregates:
1. **Portable CI Tests (185 tests)**: Unit tests, API contract tests, mock-based analyzers, temporary SQLite tests, and portable governance validations. Supported by a lightweight, purely synthetic in-memory fixture (`synthetic_ci_fixture.py`), these tests execute deterministically in clean GitHub Actions cloud runners with zero dependency on pre-existing `.db` files.
2. **Historical Data Integrity Tests (144 tests)**: Invariant audits, point-in-time filing lineage verifications, historical data readiness checks, and immutable SHA-256 database checksum assertions. These tests are explicitly marked with `@pytest.mark.requires_preseeded_db` and preserved as local pre-release and audit-gated controls.

### Empirical Verification Results
- **Pristine Fresh-Checkout Simulation** (in an isolated temporary directory containing **zero** `.db` files):
  - Portable Backend Tests: **185 passed, 144 deselected, 0 failed, 0 errors** in 12.15s.
  - Frontend Unit Tests: **143 passed, 0 failed** in 2.2s.
  - Frontend Production Build: **Vite 8.3.0 bundle generated in 964ms**.
  - Backend Docker Build: **Exit code 0 (Compiled successfully)**.
  - Frontend Docker Build: **Exit code 0 (Compiled successfully)**.
- **Local Authorized Governance Suite** (with physical databases present):
  - Full Backend Test Suite: **329 passed, 0 failed, 0 skipped** in 76.64s.
- **Safety Invariant**:
  - Production Database SHA-256: `1a2036fcc72af59b3633b5c2a077c26dd45756b3360824f36e995e2e805a28a8` (100% bit-for-bit intact).
  - Protected Strategy Logic Engines: 0 modifications to `strategy_engine.py`, `signal_engine.py`, `trade_quality_engine.py`, `portfolio_simulator.py`.
  - Git Hygiene: 0 commits, 0 pushes, 0 production databases checked into Git.

**Final Phase 3.2 Verdict:** **PHASE 3.2 COMPLETE**

---

## 1. HISTORICAL DATABASE DEPENDENCY AUDIT

An exhaustive audit of all test suites identified the exact database, table, record, and cryptographic hash dependencies across the test repository:

| Test File | Required Database | Required Tables | Required Records | Checks SHA-256 Hash? | Portable in Clean Runner? |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `test_api_contract.py` | `swing_trading.db` | `companies`, `daily_prices`, `sectors`, `industries`, `technical_indicators`, `backtest_trades` | 52 company symbols, 200 INFY candles | No | **Yes** (via `synthetic_ci_fixture.py`) |
| `test_audit_001_financial_lookahead.py` | Temporary SQLite | `quarterly_financials` | Synthetic dates | No | **Yes** (Isolated unit tests) |
| `test_audit_002_backtest_metrics.py` | In-memory SQLite | `backtest_trades` | Synthetic trade tuples | No | **Yes** (Isolated unit tests) |
| `test_audit_003_004_performance.py` | `swing_trading.db` | `companies`, `stocks`, `daily_prices`, `technical_indicators` | 52 actual companies, indicators | No | **No** (Marked `requires_preseeded_db`) |
| `test_audit_005_sequential_backtest.py` | In-memory / Mock | None (DataFrame mocks) | Synthetic OHLCV bars | No | **Yes** (Isolated unit tests) |
| `test_audit_006_independent_verification.py`| In-memory / Mock | None (DataFrame mocks) | Synthetic trade series | No | **Yes** (Isolated unit tests) |
| `test_audit_010_synthetic_trade.py` | In-memory / Mock | None (DataFrame mocks) | Synthetic trade setups | No | **Yes** (Isolated unit tests) |
| `test_audit_016_fundamental_isolation.py` | Temporary SQLite | `financial_records` (temp), asserts `prod_db.exists()` | Synthetic financial records | No | **Yes** (11 unit tests; `test_12` marked `requires_preseeded_db`) |
| `test_audit_037_historical_financial_eligibility.py` | Temporary SQLite | `quarterly_financials`, `daily_prices` | Synthetic filings | Yes (Conditional if exists) | **Yes** (31 unit tests; `test_32` conditional) |
| `test_audit_040_signal_starvation_diagnostics.py` | Mock DataFrames & `swing_trading.db` | None for logic; checks physical file for `test_10` & `ABB` for `test_08` | Mock DataFrames; `ABB` stock | Yes (`1A2036FCC72...`) | **Yes** (8 unit tests; `test_08` & `test_10` marked `requires_preseeded_db`) |
| `test_audit_041_historical_data_readiness.py` | `swing_trading.db` | `quarterly_results`, `daily_prices` | 5 quarters across 52 companies | Yes (`1A2036FCC72...`) | **No** (Marked `requires_preseeded_db`) |
| `test_audit_042_dual_setup_design.py` | `swing_trading.db` | None directly; verifies file checksum | Prod DB file | Yes (`1A2036FCC72...`) | **No** (Marked `requires_preseeded_db`) |
| `test_audit_043_controlled_prototype.py` | `swing_trading.db` & `staging_financial_expansion.db` | None directly; verifies checksums & staging schema | Both DB files | Yes (`1A2036FCC72...`) | **No** (Marked `requires_preseeded_db`) |
| `test_audit_044_pullback_validation.py` | `swing_trading.db` | `daily_prices` | Historical daily prices | Yes (`1A2036FCC72...`) | **No** (Marked `requires_preseeded_db`) |
| `test_audit_045_cost_complete.py` | `swing_trading.db` | `backtest_trades`, `daily_prices` | Historical trade logs | Yes (`1A2036FCC72...`) | **No** (Marked `requires_preseeded_db`) |
| `test_audit_046_data_readiness.py` | Mock DataFrames | None | Synthetic OHLCV series | No | **Yes** (Isolated unit tests) |
| `test_audit_047_remediation.py` | Mock DataFrames | None | Synthetic OHLCV series | No | **Yes** (Isolated unit tests) |
| `test_audit_048_pipeline_verification.py` | `swing_trading.db` | `daily_prices`, `companies` | Historical RELIANCE/TCS data | No | **No** (Marked `requires_preseeded_db`) |
| `test_audit_050_filter_integration.py` | `swing_trading.db` | `daily_prices` | 496 bars of RELIANCE daily data | No | **No** (Marked `requires_preseeded_db`) |
| `test_audit_051_execution_safety.py` | `swing_trading.db` | `companies`, `daily_prices` | Historical OHLCV rows | No | **No** (Marked `requires_preseeded_db`) |
| `test_audit_052_research_and_ledger.py` | `swing_trading.db` | `daily_prices` | Historical OHLCV rows | No | **No** (Marked `requires_preseeded_db`) |
| `test_audit_053_research_and_tariff.py` | `swing_trading.db` | `daily_prices` | Historical OHLCV rows | No | **No** (Marked `requires_preseeded_db`) |
| `test_database_configuration.py` | Temporary SQLite & `swing_trading.db` | None for proxy; `companies` for `test_read_only` & `healthz` | 52 company symbols | No | **Yes** (8 unit tests; 2 marked `requires_preseeded_db`) |
| `test_database_persistence_safety.py` | Temporary SQLite | None (verifies mount safety) | Synthetic files | No | **Yes** (Isolated unit tests) |
| `test_historical_financial_safety.py` | `swing_trading.db` | `quarterly_financials` | 5 quarters historical data | No | **No** (Marked `requires_preseeded_db`) |
| `test_p0_backtesting_quarantine_integrity.py` | Mock DataFrames | None | Synthetic anomaly data | No | **Yes** (Isolated unit tests) |
| `test_p1_point_in_time_financial_integrity.py` | `swing_trading.db` | `quarterly_financials` | Historical filing dates | No | **No** (Marked `requires_preseeded_db`) |
| `test_p1_strict_pipeline_integration.py` | Mock DataFrames | None | Synthetic filing objects | No | **Yes** (Isolated unit tests) |
| `test_p2_14_pit_governance.py` | `staging_financial_expansion.db` | `quarterly_financial_vintages` | 28 historical vintages | Yes (`534e42a8...`, `dc564e8b...`) | **No** (Marked `requires_preseeded_db`) |
| `test_p2_6_schema_lineage.py` | Temporary SQLite & `staging_financial_expansion.db` | `quarterly_financial_vintages` | 17 legacy vintages for `test_11` | No | **Yes** (10 unit tests; `test_11` marked `requires_preseeded_db`) |
| `test_p2_7_to_p2_11.py` | `staging_financial_expansion.db` | `quarterly_financial_vintages` | 28 historical vintages | No | **No** (Marked `requires_preseeded_db`) |
| `test_p2_financial_ingestion_pilot.py` | Temporary SQLite & `staging_financial_expansion.db` | `quarterly_financial_vintages` | TCS Q1/Q2 for `test_05` | No | **Yes** (5 unit tests; `test_05` marked `requires_preseeded_db`) |
| `test_p2_pilot_remediation.py` | `staging_financial_expansion.db` & `swing_trading.db` | `quarterly_financial_vintages`, `staging_filings_store` | Remediated vintages 1-10, 18-21 | Yes (`1a2036fc...`) | **No** (Marked `requires_preseeded_db`) |
| `test_p2_staging_financial_vintage.py` | Temporary SQLite | `quarterly_financial_vintages` | Synthetic test vintages | No | **Yes** (Isolated unit tests) |

---

## 2. TEST CATEGORIZATION STRATEGY

To preserve 100% test rigor without weakening assertions or publishing proprietary financial records to cloud runners, tests are partitioned into two distinct categories:

```
+---------------------------------------------------------------------------------------+
|                               TEST CATEGORIZATION MATRIX                              |
+---------------------------------------------------------------------------------------+
|                                                                                       |
|   CATEGORY A: PORTABLE CI TESTS (185 Tests)                                           |
|   -----------------------------------------                                           |
|   Target Environment: GitHub-Hosted Runner (ubuntu-latest)                            |
|   Invocation:         pytest -m "not requires_preseeded_db" backend/tests/            |
|   Characteristics:    - Zero dependency on physical .db files in Git checkout         |
|                       - Uses synthetic in-memory fixture (synthetic_ci_fixture.py)    |
|                       - Tests core logic, math, indicator formulas, and edge cases    |
|                       - Verifies FastAPI routing, error handling (404/422), schemas   |
|                                                                                       |
|   CATEGORY B: HISTORICAL DATA INTEGRITY TESTS (144 Tests)                             |
|   -------------------------------------------------------                             |
|   Target Environment: Authorized Local Workstation / Secure Pre-Release Gate          |
|   Invocation:         pytest backend/tests/ (Runs all 329 tests)                      |
|   Characteristics:    - Asserts exact cryptographic SHA-256 database checksums        |
|                       - Asserts exact historical row counts (e.g. 28 vintages, 5 Qs)   |
|                       - Validates Point-in-Time financial governance and remediations |
|                       - Never executed in unseeded runners; never skipped silently    |
|                                                                                       |
+---------------------------------------------------------------------------------------+
```

---

## 3. TEST ARCHITECTURE IMPLEMENTATION

### A. Pytest Marker Registration (`pytest.ini`)
Created `pytest.ini` in the repository root to formally register the `requires_preseeded_db` marker, define standard options, and silence deprecation noise:

```ini
[pytest]
markers =
    requires_preseeded_db: Historical financial governance and data integrity tests requiring local pre-seeded databases (swing_trading.db or staging_financial_expansion.db)
testpaths = backend/tests
addopts = -v --tb=short
filterwarnings =
    ignore::DeprecationWarning
    ignore::UserWarning
    ignore::FutureWarning
```

### B. Synthetic CI Fixture Generator (`backend/tests/fixtures/synthetic_ci_fixture.py`)
Developed a minimal, non-sensitive, purely synthetic SQLite test database fixture specifically for portable CI contract testing.
- **Provenance & Safety**: Contains 0 authentic financial records and 0 real market prices.
- **Schema**: Generates tables (`companies`, `daily_prices`, `quarterly_results`, `technical_indicators`, `financial_scores`, `opportunity_scores`, `signals`, `sectors`, `industries`, `backtest_runs`, `backtest_trades`, `backtest_equity_curve`) directly matching backend expectations.
- **Seeding**: Seeds 52 synthetic company symbols (`INFY` + 51 stubs), 200 synthetic OHLCV bars for `INFY`, and 5 sector categories.

### C. Automatic Test Environment Adapter (`backend/tests/conftest.py`)
Configured a session-level autouse fixture:
- When running in an environment where `database/swing_trading.db` is present (local workstation), it preserves default local database paths.
- When running in an environment where `database/swing_trading.db` is absent (clean CI checkout), it initializes an isolated temporary synthetic database and exports `DATABASE_PATH` for the test session.

---

## 4. GITHUB ACTIONS WORKFLOW UPDATES

Updated [.github/workflows/ci.yml](file:///c:/Users/vigne/OneDrive/Desktop/projects/swing-trading-tool/.github/workflows/ci.yml) to reflect the portable CI architecture:

```yaml
name: Continuous Integration

on:
  push:
    branches:
      - main
  pull_request:
    branches:
      - main
  workflow_dispatch:

permissions:
  contents: read

concurrency:
  group: ${{ github.workflow }}-${{ github.ref }}
  cancel-in-progress: true

jobs:
  backend-ci:
    name: Backend Tests & Governance Audit
    runs-on: ubuntu-latest
    timeout-minutes: 15

    steps:
      - name: Checkout repository
        uses: actions/checkout@11bd71901bbe5b1630ceea73d27597364c9af683 # v4.2.2

      - name: Set up Python 3.11
        uses: actions/setup-python@0b93645e9fea7318ecaed2b359559ac225c90a2b # v5.3.0
        with:
          python-version: '3.11'
          cache: 'pip'
          cache-dependency-path: backend/requirements.txt

      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -r backend/requirements.txt
          pip install -r backend/requirements-dev.txt

      - name: Run backend portable test suite
        env:
          PYTHONUTF8: '1'
        run: |
          python -m pytest -m "not requires_preseeded_db" backend/tests/ -v --tb=short

      - name: Generate test summary
        if: always()
        run: |
          echo "### Backend Portable CI Summary" >> $GITHUB_STEP_SUMMARY
          echo "Python Version: 3.11" >> $GITHUB_STEP_SUMMARY
          echo "Test Suite Directory: backend/tests/" >> $GITHUB_STEP_SUMMARY
          echo "Test Selection: Portable CI (-m 'not requires_preseeded_db')" >> $GITHUB_STEP_SUMMARY
          echo "Status: Complete" >> $GITHUB_STEP_SUMMARY

  frontend-ci:
    name: Frontend Tests & Production Build
    runs-on: ubuntu-latest
    timeout-minutes: 10

    steps:
      - name: Checkout repository
        uses: actions/checkout@11bd71901bbe5b1630ceea73d27597364c9af683 # v4.2.2

      - name: Set up Node.js 20
        uses: actions/setup-node@39370e3970a6d050c480ffad4ff0ed4d3fdee5af # v4.1.0
        with:
          node-version: 20
          cache: 'npm'
          cache-dependency-path: frontend/package-lock.json

      - name: Install dependencies
        run: npm --prefix frontend ci

      - name: Run frontend unit tests
        run: npm --prefix frontend test

      - name: Run frontend production build
        run: npm --prefix frontend run build

      - name: Generate frontend summary
        if: always()
        run: |
          echo "### Frontend CI Summary" >> $GITHUB_STEP_SUMMARY
          echo "Node Version: 20" >> $GITHUB_STEP_SUMMARY
          echo "Build Target: Vite Production Bundle" >> $GITHUB_STEP_SUMMARY
          echo "Status: Complete" >> $GITHUB_STEP_SUMMARY

  docker-validation:
    name: Docker Image Build Validation
    runs-on: ubuntu-latest
    timeout-minutes: 15
    needs: [backend-ci, frontend-ci]

    steps:
      - name: Checkout repository
        uses: actions/checkout@11bd71901bbe5b1630ceea73d27597364c9af683 # v4.2.2

      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@6524bf65af31da8d45b59e8c27de4bd072b392f5 # v3.8.0

      - name: Validate Backend Docker Image Build
        uses: docker/build-push-action@ca052bb54ab0790a636c9b5f226502c73d547a25 # v5.4.0
        with:
          context: .
          file: backend/Dockerfile
          push: false
          tags: swing-trading-backend:ci-validation

      - name: Validate Frontend Docker Image Build
        uses: docker/build-push-action@ca052bb54ab0790a636c9b5f226502c73d547a25 # v5.4.0
        with:
          context: ./frontend
          file: frontend/Dockerfile
          build-args: |
            VITE_API_BASE_URL=http://localhost:8000
          push: false
          tags: swing-trading-frontend:ci-validation
```

---

## 5. FRESH-CHECKOUT SIMULATION VERIFICATION

To guarantee that the CI pipeline will execute without errors on a clean GitHub-hosted runner, an automated simulation script (`scratch/simulate_fresh_ci.py`) was executed in an isolated temporary directory.

### Simulation Protocol
1. Created an isolated temporary directory (`C:\Users\vigne\AppData\Local\Temp\ci_clean_checkout_8jv2uibe`).
2. Cloned workspace files strictly excluding all `.db` and `.sqlite` files.
3. Verified physical file count: **0 database files in the checkout**.
4. Executed all 5 pipeline verification steps.

### Simulation Results

| CI Pipeline Stage | Executed Command | Exit Code | Empirical Result |
| :--- | :--- | :--- | :--- |
| **Backend Portable Pytest** | `python -m pytest -m "not requires_preseeded_db" backend/tests/ -v --tb=short` | `0` | **185 passed, 144 deselected** in 12.15s |
| **Frontend Unit Tests** | `npm --prefix frontend test` | `0` | **143 passed, 0 failed** across all 4 sub-suites |
| **Frontend Production Build** | `npm --prefix frontend run build` | `0` | **Vite v8.3.0 bundle built in 964ms** |
| **Backend Docker Build** | `docker build -t swing_trading_backend:ci_sim -f backend/Dockerfile .` | `0` | **Success (Image compiled cleanly)** |
| **Frontend Docker Build** | `docker build -t swing_trading_frontend:ci_sim -f frontend/Dockerfile ./frontend` | `0` | **Success (Image compiled cleanly)** |

**Clean Runner Simulation Status:** **ALL PASS (100%)**

---

## 6. HISTORICAL GOVERNANCE VERIFICATION (LOCAL ENVIRONMENT)

The complete historical governance suite was executed locally in the authorized workstation environment against the genuine databases:

- **Command**: `python -m pytest backend/tests/ -q`
- **Result**: **329 passed, 0 failed, 0 skipped** in 76.64s.
- **Integrity**: All 144 historical governance assertions passed with 100% fidelity:
  - `test_audit_040` (Signal starvation & SHA-256 invariance: PASSED)
  - `test_audit_041` (Historical data readiness & 5 quarters per company: PASSED)
  - `test_audit_042` to `test_audit_045` (Strategy dual-setups & cost models: PASSED)
  - `test_p2_14_pit_governance` (15 PIT governance assertions & staging hash: PASSED)
  - `test_p2_pilot_remediation` (Preserved pilot records & SHA-256 invariance: PASSED)
  - `test_p2_7_to_p2_11` (20 authentic document & historical scenarios: PASSED)

---

## 7. SECURITY AND GOVERNANCE SAFETY AUDIT

| Invariant / Check | Requirement | Audit Result | Status |
| :--- | :--- | :--- | :--- |
| **Production DB Checksum** | `1a2036fcc72af59b3633b5c2a077c26dd45756b3360824f36e995e2e805a28a8` | `1A2036FCC72AF59B3633B5C2A077C26DD45756B3360824F36E995E2E805A28A8` | **UNMODIFIED** |
| **Protected Logic Engines** | 0 edits to strategy, signal, quality, simulator | `git diff backend/logic/` confirmed 0 modifications | **UNMODIFIED** |
| **Financial Records Privacy** | No proprietary databases in Git / CI artifacts | `database/*.db` strictly gitignored; 0 DB files pushed | **ENFORCED** |
| **Action Supply Chain** | All 5 actions pinned to 40-char commit SHAs | Verified immutable commit SHAs in `ci.yml` | **ENFORCED** |
| **Workflow Permissions** | Minimum privilege | `permissions: contents: read` enforced | **ENFORCED** |
| **Git Commit Hygiene** | No unauthorized commits or pushes | 0 commits, 0 pushes executed | **ENFORCED** |

---

## 8. REMAINING LIMITATIONS AND CLOUD REALITIES

1. **Dual-Environment Test Division**:
   - In cloud GitHub Actions runners, only the 185 portable CI tests execute.
   - The 144 historical governance tests asserting exact cryptographic database hashes and authentic exchange filings remain local pre-release gates. This is an intentional architectural design: publishing the production database to public GitHub runners would compromise data privacy and bloat repository bandwidth.
2. **SQLite Single-Writer Concurrency**:
   - Cloud deployments (Render) must continue operating as a single web container (`replicas: 1`) attached to a persistent disk (`/data`). Horizontal autoscaling requires migrating the storage tier to Managed PostgreSQL in Phase 5.

---

## 9. FINAL VERDICT AND READINESS ASSESSMENT

```
================================================================================
                           FINAL AUDIT VERDICT
================================================================================

                         VERDICT: PHASE 3.2 COMPLETE

1. Cloud Runner Portability: 100% VERIFIED (Simulated clean checkout: ALL PASS)
2. Portable Test Suite:     100% PASS (185 passed in 12.15s, 0 DB files needed)
3. Historical Governance:   100% PASS (329/329 passed locally in 76.64s)
4. CI Workflow Hardening:   100% VERIFIED (Action SHAs pinned, least privilege)
5. Safety Invariants:       100% VERIFIED (DB SHA-256 untouched, 0 git commits)
================================================================================
```

*Phase 3, Phase 3.1, and Phase 3.2 are complete. The CI/CD infrastructure is fully validated and ready for Phase 4 upon explicit user authorization.*

