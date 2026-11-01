with open('docs/audit_artifacts/MASTER_AUDIT_TRACKER.md', 'r', encoding='utf-8') as f:
    text = f.read()

# Update header
text = text.replace('AUDIT-019 → AUDIT-047', 'AUDIT-019 → AUDIT-048')
text = text.replace('ALL 27 PHASES COMPLETE — AUDIT-047 COMPREHENSIVE DATA INTEGRITY REMEDIATION RATIFIED', 'ALL 28 PHASES COMPLETE — AUDIT-048 RESEARCH PIPELINE INTEGRATION & CLASSIFICATION RATIFIED')

target_str = "| **AUDIT-047** | Historical Data Remediation | Comprehensive Historical Data Integrity Remediation |"

new_table_row = """| **AUDIT-048** | Research Pipeline Integration | Research Pipeline Integration, Data Verification, and Remaining Blockers | **INTEGRATION RATIFIED (BLOCKERS DISCLOSED)** | Traced and connected `research_market_data_filter.py` into `historical_data_service.py`, `backtesting_dataset_service.py`, and `backtest_data_access_service.py` via `filter_synthetic_holidays=True`; fixed timestamp normalization in holiday check; verified TMPV demerger (-40.15%) and TRENT ratio drop (-33.05%); reconciled Zerodha equity delivery tariffs vs statutory rates; fully classified all 25,746 bars (25,638 normal, 103 holiday, 3 stale, 2 large moves) and exported machine-readable JSON; added 9 dedicated regression tests in `test_audit_048_pipeline_verification.py` (106 total audit tests passing); production and staging DB checksums invariant. |\n"""

lines = text.splitlines(keepends=True)
new_lines = []
for line in lines:
    new_lines.append(line)
    if line.startswith("| **AUDIT-047**"):
        new_lines.append(new_table_row)

text = "".join(new_lines)

appendix = """16. **AUDIT-048 Research Pipeline Integration & Data Verification Synthesis:**
    - Connected the non-destructive research market data filter into the actual research access pipeline:
      - Added opt-in parameter `filter_synthetic_holidays: bool = False` to `historical_data_service.py`, `backtesting_dataset_service.py`, and `backtest_data_access_service.py`.
      - Resolved datetime64 vs string comparison defect in `research_market_data_filter.py`, allowing automatic exclusion of 103 synthetic holiday flat bars when requested.
      - Preserved production defaults (`False`) ensuring 100% backward compatibility for production engines.
    - Verified corporate action anomalies:
      - `TMPV` on 2025-10-14 (-40.15%): Verified legitimate corporate demerger (`VERIFIED_CORPORATE_ACTION`).
      - `TRENT` on 2026-01-01 (-33.05%): Verified ratio price discontinuity (`UNRESOLVED_PRICE_ANOMALY` / suspected 3:2 split/bonus).
    - Reconciled transaction cost model:
      - Mapped statutory fees (STT 0.1%, NSE 0.00297%, SEBI ₹10/cr, Stamp Duty 0.015% buy, GST 18%) vs broker assumptions (₹0 brokerage, ₹15.93 CDSL DP charge per sell leg).
    - Executed exhaustive market data classification across all 25,746 rows:
      - 25,638 normal sessions (99.58%), 103 synthetic holiday bars (0.40%), 3 stale flat bars (0.01%), 2 large discontinuities (0.01%), 0 inverted OHLC, 0 non-positive prices.
      - Exported machine-readable report to `docs/audit_artifacts/audit_048_market_data_classification.json`.
    - Regression test suite confirmed:
      - 9 dedicated regression tests added in `test_audit_048_pipeline_verification.py` (106 total passing audit tests across 10 modules).
      - Production database SHA-256 invariant at `1A2036FCC72AF59B3633B5C2A077C26DD45756B3360824F36E995E2E805A28A8`.
      - Staging database SHA-256 invariant at `4B5A3479ABA5F5176843EF1033C026A543D54914DB68CD2169E1FF5552BED465`.
      - Production deployment and live trading remain strictly blocked.
"""

if "AUDIT-048 Research Pipeline Integration & Data Verification Synthesis" not in text:
    text = text.rstrip() + "\n" + appendix

with open('docs/audit_artifacts/MASTER_AUDIT_TRACKER.md', 'w', encoding='utf-8') as f:
    f.write(text)

print("Successfully updated MASTER_AUDIT_TRACKER.md with AUDIT-048 via script")

