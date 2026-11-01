with open('docs/audit_artifacts/MASTER_AUDIT_TRACKER.md', 'r', encoding='utf-8') as f:
    text = f.read()

text = text.replace(
    '# MASTER AUDIT TRACKER: AUDIT-019 \u2192 AUDIT-051',
    '# MASTER AUDIT TRACKER: AUDIT-019 \u2192 AUDIT-052'
)
text = text.replace(
    'Last Updated: 2026-11-01T20:07:00+05:30',
    'Last Updated: 2026-11-01T20:16:00+05:30'
)
text = text.replace(
    'Status: ALL 31 PHASES COMPLETE \u2014 AUDIT-051 RESEARCH EXECUTION SAFETY & SAFEGUARDS RATIFIED',
    'Status: ALL 32 PHASES COMPLETE \u2014 AUDIT-052 FINAL RESEARCH SAFETY & ACTUAL LEDGER RECONCILIATION RATIFIED'
)

marker = "| **AUDIT-051** | Research Execution Safety"
pos = text.find(marker)
if pos != -1:
    end_of_line = text.find("\n", pos)
    new_row = "\n| **AUDIT-052** | Final Research & Ledger Verification | Final Research Safety Verification and Actual Transaction Ledger Reconciliation | **PASS WITH LIMITATIONS (LEDGER & DATASET VERIFIED)** | Verified final research dataset enforcement across all 5 entry points; proved zero downstream reloads; proved fail-visible anomaly halts on TRENT; reconciled actual transaction ledger in portfolio_simulator (exact cash/equity equality, zero fee double-counting, exact Rs 238.18 round-trip cash debit); added test_audit_052_research_and_ledger.py (9/9 passed); 128 dedicated audit tests passing; DB hashes 100% invariant; live trading strictly blocked. |"
    text = text[:end_of_line] + new_row + text[end_of_line:]

section_20 = """

20. **AUDIT-052 Final Research Safety & Actual Ledger Reconciliation Synthesis:**
    - Priority 1 (Final Research Dataset Enforcement):
      - Verified that `build_backtesting_dataset` and `get_backtest_inputs` enforce holiday filtering and pass clean 494-bar series to downstream simulators.
      - Proved that no downstream service silently reloads unfiltered SQLite data.
      - Proved that `validate_research_dataset_safety` halts on unadjusted anomalies (`TRENT` on 2026-01-01) and that quarantine mode removes the unadjusted drop cleanly.
    - Priority 2 (Actual Transaction-Ledger Reconciliation):
      - Fully reconciled the DP fee discrepancy: Statutory CDSL tariff of Rs 13.50 base fee + Rs 2.43 GST (18%) = Rs 15.93 actual cash debit per sell transaction.
      - Mapped exact taxable base for GST: Brokerage (Rs 0.00) + NSE fee (Rs 2.97) + SEBI fee (Rs 0.10) + Base DP fee (Rs 13.50); STT and Stamp Duty are statutory taxes exempt from GST.
      - Proved that `portfolio_simulator.py` debits fees exactly once: verified that across single and multi-trade backtests, $\\text{Final Cash} = \\text{Initial Cash} + \\text{Gross P&L} - \\text{Total Costs}$ without duplicate charges or omissions.
      - Reconciled display rounding: Internal calculations preserve 4-decimal precision; summary output formats to 2 decimal places. The 1-cent difference between component sums (Rs 238.17) and exact cash outflow (Rs 238.18) is purely an intermediate rounding artifact.
    - Test Suite Execution:
      - Authored and passed `backend/tests/test_audit_052_research_and_ledger.py` (9 tests, all passing).
      - Core backend suite: 856 tests passed. Total dedicated audit tests: 128 tests across 13 modules.
    - Invariants and Safety:
      - Production DB SHA-256 invariant at `1A2036FCC72AF59B3633B5C2A077C26DD45756B3360824F36E995E2E805A28A8`.
      - Staging DB SHA-256 invariant at `4B5A3479ABA5F5176843EF1033C026A543D54914DB68CD2169E1FF5552BED465`.
      - Protected strategy files unmodified; production deployment and live trading remain strictly blocked.
"""
text = text + section_20

with open('docs/audit_artifacts/MASTER_AUDIT_TRACKER.md', 'w', encoding='utf-8') as f:
    f.write(text)
print('Successfully updated MASTER_AUDIT_TRACKER.md for AUDIT-052')

