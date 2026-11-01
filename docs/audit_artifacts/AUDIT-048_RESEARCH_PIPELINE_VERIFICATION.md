# AUDIT-048: Research Pipeline Integration, Data Verification, and Remaining Blockers

**Project:** Swing Trading Intelligence Platform — Indian Equities  
**Repository:** `c:\Users\vigne\OneDrive\Desktop\projects\swing-trading-tool`  
**Current Baseline Commit:** `dc0555e39024ba075dc93da7d59896e8037a3be9`  
**Production Database:** `database/swing_trading.db`  
**Staging Database:** `database/staging_financial_expansion.db`  
**Audit Date:** 2026-11-01  
**Status:** RESEARCH PIPELINE INTEGRATION RATIFIED — REMAINING BLOCKERS DISCLOSED

---

## 1. Executive Summary & Verification Outcomes

AUDIT-048 independently investigated whether the data integrity remediations and anomaly detection utilities authored in AUDIT-047 actually function throughout the end-to-end research pipeline:

1. **Research Filter Pipeline Integration (PASS):**
   - Discovered that the AUDIT-047 `research_market_data_filter.py` was previously an isolated utility not invoked by data-access paths.
   - Connected `filter_research_market_data` into `historical_data_service.py`, `backtesting_dataset_service.py`, and `backtest_data_access_service.py` via an explicit opt-in parameter (`filter_synthetic_holidays=True`).
   - Resolved a critical datetime normalization defect where `datetime64[us]` timestamps failed string set membership against `KNOWN_EXCHANGE_HOLIDAYS`.
2. **Corporate Action Anomaly Verification (VERIFIED & DOCUMENTED):**
   - **`TMPV` (-40.15% on 2025-10-14):** Confirmed as a legitimate corporate demerger of Tata Motors commercial and passenger vehicle divisions (`VERIFIED_CORPORATE_ACTION`).
   - **`TRENT` (-33.05% on 2026-01-01):** Confirmed as a price discontinuity (`UNRESOLVED_PRICE_ANOMALY` / suspected 3:2 bonus/split or unadjusted provider adjustment; ratio = 0.6752).
3. **Transaction Cost Model Tariff Verification (VERIFIED WITH ASSUMPTIONS):**
   - Reconciled Zerodha equity delivery tariffs against statutory SEBI and Indian Ministry of Finance rules.
   - Verified that DP charges (₹15.93 per sell leg) are depository charges that are not universal across all brokers and account types.
4. **Full Market Data Classification (EXPORTED & VERIFIED):**
   - Scanned all 25,746 rows across 52 stocks:
     - `NORMAL_SESSION`: 25,638 bars (99.58%).
     - `SYNTHETIC_HOLIDAY_BAR`: 103 bars on exchange holidays (Holi `2025-03-18`, Sankranti `2026-01-15`).
     - `STALE_FLAT_BAR`: 3 bars on regular trading sessions (`M&M`, `ETERNAL`).
     - `LARGE_PRICE_DISCONTINUITY`: 2 bars (`TMPV`, `TRENT`).
     - `INVERTED_OHLC`: 0 violations.
     - `NON_POSITIVE_PRICE`: 0 violations.
   - Exported complete machine-readable report to [`docs/audit_artifacts/audit_048_market_data_classification.json`](file:///c:/Users/vigne/OneDrive/Desktop/projects/swing-trading-tool/docs/audit_artifacts/audit_048_market_data_classification.json).
5. **Regression Verification:** All 106 audit regression tests across 10 modules pass green. Both SQLite database checksums remain 100% invariant.

---

## 2. Research Pipeline Call Graph & Integration Architecture

Prior to AUDIT-048, research filter utilities existed only in isolation. The integration was traced and safely connected across the research access hierarchy:

```mermaid
flowchart TD
    DB[("SQLite: daily_prices (Raw)")] --> DS["data_service.py (get_stock_data)"]
    DS --> HDS["historical_data_service.py (get_historical_data)"]
    
    subgraph "AUDIT-048 Filter Integration Layer"
        HDS -->|"filter_synthetic_holidays=True"| RMF["research_market_data_filter.py (filter_research_market_data)"]
        RMF -->|"Cleaned OHLCV (103 Holiday Bars Excluded)"| CleanDF["Cleaned Market DataFrame"]
    end
    
    HDS -->|"filter_synthetic_holidays=False (Default)"| RawDF["Raw Market DataFrame (Preserved)"]
    
    CleanDF --> BDS["backtesting_dataset_service.py (build_backtesting_dataset)"]
    RawDF --> BDS
    
    BDS --> BDAS["backtest_data_access_service.py (get_backtest_inputs)"]
    
    BDAS --> RE["Research Engines (backend/experimental/)"]
    
    subgraph "Protected Production Layer (Untouched)"
        SE["strategy_engine.py"]
        SIG["signal_engine.py"]
        PS["portfolio_simulator.py"]
    end
```

### Safety & Invariance Contract
- Production defaults remain `filter_synthetic_holidays=False`, preserving 100% backward compatibility for production test suites.
- Research backtests and experimental prototypes explicitly pass `filter_synthetic_holidays=True` to exclude the 103 synthetic flat bars without mutating the database.

---

## 3. Comprehensive Issue & Remediation Table

| Issue | Forensic Evidence | Root Cause | Fix Implemented | Regression Test | Historical Data Limitation | Status |
| :--- | :--- | :--- | :--- | :--- | :--- | :---: |
| **1. Filter Pipeline Decoupling** | `research_market_data_filter.py` had 0 inbound imports in `backend/` codebase. | Filtering utility was created in AUDIT-047 as an isolated tool. | Added `filter_synthetic_holidays` parameter across `historical_data_service.py`, `backtesting_dataset_service.py`, and `backtest_data_access_service.py`. Fixed datetime normalization bug in `research_market_data_filter.py`. | `test_01`, `test_02`, `test_03` in `test_audit_048_pipeline_verification.py` | Production SQLite database retains raw records; research callers must explicitly enable the filter flag. | **PASS (Integrated & Tested)** |
| **2. Corporate Action Anomalies** | `TMPV` (-40.15% on 2025-10-14), `TRENT` (-33.05% on 2026-01-01) produced large price drops in raw data. | `TMPV` experienced a corporate demerger. `TRENT` had an unadjusted ratio drop (0.6752) matching a suspected split/bonus. Raw close was unadjusted in provider feed. | Implemented large price discontinuity detection in `research_market_data_filter.py`. Preserved raw prices for execution while flagging anomalies for corporate action auditing. | `test_04`, `test_05` in `test_audit_048_pipeline_verification.py` | Historical corporate actions table not yet persisted in SQLite database. Discontinuities remain unadjusted in raw prices. | **PARTIAL (Safeguards Verified, Historical Ingestion Pending)** |
| **3. Transaction Cost Tariffs** | Zerodha delivery model assumes ₹0 brokerage, 0.1% STT, 0.00297% NSE fees, ₹10/cr SEBI fee, 0.015% stamp duty, 18% GST, and ₹15.93 CDSL DP charge. | Tariffs reflect current standard discount broker equity delivery rules, but DP charges and brokerage models vary across brokers and institutional accounts. | Audited itemized cost calculation in `cost_model.py`. Reconciled buy vs sell cost components. Documented broker-specific DP charges as research assumptions rather than universal statutory fees. | `test_06`, `test_07` in `test_audit_048_pipeline_verification.py` | Historical tariff variations (e.g. pre-2020 stamp duty rates, institutional broker fees) are not modeled point-in-time. | **PASS WITH LIMITATIONS (Tariff Assumptions Disclosed)** |
| **4. Full Market Data Universe Classification** | Suspected 103 holiday flat bars, 3 stale flat bars, and 2 large moves required exhaustive re-scan. | Provider carried forward previous close with Volume = 0 on exchange holidays. | Re-scanned all 25,746 rows across 52 stocks using `detect_market_data_anomalies`. Exported full machine-readable JSON inventory report. | `test_08`, `test_09` in `test_audit_048_pipeline_verification.py` | Raw holiday bars remain in SQLite database; research callers must invoke filtering layer. | **PASS (Fully Classified & Exported)** |

---

## 4. Full Market-Data Universe Classification Breakdown

From the execution of [`scratch/audit_048_classify_all_market_data.py`](file:///c:/Users/vigne/OneDrive/Desktop/projects/swing-trading-tool/scratch/audit_048_classify_all_market_data.py) against `database/swing_trading.db`:

- **Total Rows Examined:** 25,746
- **Unique Symbols:** 52
- **Unique Dates:** 496 (spanning 2024-10-23 to 2026-10-23)
- **Duplicate (symbol, date) Keys:** 0
- **Mathematical Inverted OHLC Violations ($H < L$ or $O, C \notin [L, H]$):** 0
- **Non-Positive Prices ($\le 0$):** 0
- **Negative Volume Records:** 0

### Classification Breakdown
1. **`NORMAL_SESSION`:** **25,638 rows (99.58%)**
   - Active, liquid trading sessions with valid non-zero volume and ordinary price fluctuation.
2. **`SYNTHETIC_HOLIDAY_BAR`:** **103 rows (0.40%)**
   - Confirmed exchange holidays where the provider carried forward the previous day's close with Volume = 0:
     - `2025-03-18` (Holi): 51 stocks.
     - `2026-01-15` (Makar Sankranti / Municipal Election): 52 stocks.
3. **`STALE_FLAT_BAR`:** **3 rows (0.01%)**
   - Isolated stale bars on normal trading days:
     - `M&M` on `2025-09-08`: $O=H=L=C=3561.30$, Volume = 0.
     - `ETERNAL` on `2025-04-11` & `2025-04-15`: $O=H=L=C=211.39$, Volume = 0.
4. **`LARGE_PRICE_DISCONTINUITY`:** **2 rows (0.01%)**
   - Unadjusted single-day price drops $> 25\%$:
     - `TMPV` on `2025-10-14` (-40.15%): Corporate demerger.
     - `TRENT` on `2026-01-01` (-33.05%): Ratio price drop.

---

## 5. Transaction Cost Model Reconciliation

| Tariff Component | Assumed Rate / Formula | Buy Side | Sell Side | Regulatory / Commercial Source | Classification |
| :--- | :---: | :---: | :---: | :--- | :---: |
| **Brokerage** | 0.0% (Zero) | Yes | Yes | Zerodha Equity Delivery Tariff | Broker Assumption |
| **Securities Transaction Tax (STT)** | 0.10% (0.001) | Yes | Yes | Union Budget Finance Act / CBDT | Statutory Verified |
| **NSE Exchange Turnover Charges** | 0.00297% (0.0000297) | Yes | Yes | NSE Circular on Transaction Charges | Exchange Verified |
| **SEBI Turnover Charges** | ₹10 / crore (0.0001%) | Yes | Yes | SEBI (Payment of Fees) Regulations | Statutory Verified |
| **Stamp Duty** | 0.015% (0.00015) | **Yes** | **No (0.0%)** | Indian Stamp Act (2020 Amendment) | Statutory Verified |
| **Goods and Services Tax (GST)** | 18% on (Brokerage + Exchange + SEBI) | Yes | Yes | Central GST Act / State GST Rules | Statutory Verified |
| **Depository Participant (DP) Charge**| ₹15.93 (₹13.50 + 18% GST) | **No** | **Yes** | CDSL / Zerodha Depository Tariff | Broker Assumption |
| **Execution Slippage** | 0.05% to 0.10% (5-10 bps) | Yes | Yes | Execution Assumption | Research Model |

### Reconciliation
- Single-leg buy of ₹100,000 turnover:
  $\text{Costs} = ₹0 (\text{Brokerage}) + ₹100 (\text{STT}) + ₹2.97 (\text{NSE}) + ₹0.10 (\text{SEBI}) + ₹15 (\text{Stamp Duty}) + ₹0.5526 (\text{GST}) = \mathbf{₹118.62}$.
- Single-leg sell of ₹100,000 turnover:
  $\text{Costs} = ₹0 + ₹100 + ₹2.97 + ₹0.10 + ₹0 + ₹0.5526 = \mathbf{₹103.62}$ (+ ₹15.93 DP charge if delivery = **₹119.55**).

---

## 6. Final Decision Categories

| Category | Description | Status | Evidence & Quantitative Justification |
| :--- | :--- | :---: | :--- |
| **A** | **Research-Filter Integration** | **PASS** | `filter_synthetic_holidays` wired into `historical_data_service.py`, `backtesting_dataset_service.py`, and `backtest_data_access_service.py`. |
| **B** | **Market-Data Integrity** | **PASS WITH LIMITATIONS** | 25,638 normal bars valid; 103 holiday flat bars isolated and filtered. Production DB retains raw records. |
| **C** | **Corporate-Action Integrity** | **PARTIAL** | `TMPV` confirmed demerger; `TRENT` flagged discontinuity. Anomaly detection active; historical corporate actions table pending. |
| **D** | **Transaction-Cost Implementation** | **PASS** | Exact itemized calculation of STT, NSE, SEBI, Stamp Duty, GST, and broker assumptions verified. |
| **E** | **External Tariff Verification** | **PASS WITH LIMITATIONS** | Statutory rates verified against SEBI/Stamp Act; DP fee (₹15.93) and ₹0 brokerage documented as Zerodha-specific assumptions. |
| **F** | **Financial Publication-Time Reliability** | **PARTIAL** | 45-day statutory fallback enforced in code; 260 DB records lack exchange filing timestamps. |
| **G** | **Historical-Universe Integrity** | **PARTIAL** | Fixed 52-stock survivor sample. Documented in metadata; point-in-time constituent rebalancing history pending. |
| **H** | **Backtest Reproducibility** | **PASS** | 100.0% deterministic multi-year simulation across repeated independent test runs. |
| **I** | **Technical Exploratory Research Readiness** | **PASS WITH LIMITATIONS** | Pure price-action research is viable using the research filtering layer across the 52-stock survivor universe. |
| **J** | **Fundamental Research Readiness** | **BLOCKED** | Blocked by 11-month financial cold-start blackout (missing pre-2025 financial statements). |
| **K** | **Historical Constituent Research Readiness** | **BLOCKED** | Blocked by absence of historical Nifty 50 constituent addition/deletion dates prior to August 2026. |
| **L** | **Production Integration Readiness** | **STRICTLY BLOCKED** | Experimental prototypes cannot be merged into production engines. |
| **M** | **Live-Trading Readiness** | **STRICTLY BLOCKED** | Automated live trading remains completely prohibited. |

---

## 7. System Checksums & Invariants

1. **Production Database Checksum:**
   ```
   SHA-256: 1A2036FCC72AF59B3633B5C2A077C26DD45756B3360824F36E995E2E805A28A8 (100% Invariant)
   File Size: 9,068,544 bytes
   ```
2. **Staging Database Checksum:**
   ```
   SHA-256: 4B5A3479ABA5F5176843EF1033C026A543D54914DB68CD2169E1FF5552BED465 (100% Invariant)
   File Size: 5,410,816 bytes
   ```
3. **Protected Strategy Files:** Untouched.
4. **Audit Test Suites Execution:**
   - 106 tests passed in 2.45s across 10 audit test modules.
   - Core backend suite: 856 passed, 79 subtests passed.
   - Frontend suite: 288 passed.
5. **Git Tree State:** Clean uncommitted working tree; zero commits, zero pushes.

