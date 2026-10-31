# AUDIT-018: Independent Reproduction and Accounting Audit of the SUNPHARMA Trade

**Audit Execution Date:** 2026-10-29  
**Execution Environment:** Python 3.14 / SQLite 3 / Pandas 2.2  
**Database Evaluated:** `docs/audit_artifacts/temp_pilot_audit_018.db`  
**Auditor:** Independent Verification Engineer  

---

## 1. Executive Summary

AUDIT-017 reported that across the 52-stock universe during the 6-month simulation period (`2025-10-01` to `2026-03-31`), exactly **one trade** qualified and executed: `SUNPHARMA`, generating a net profit of **₹978.32**.

This audit performed an independent, end-to-end trace from raw historical price bars and quarterly records through the decision engine, signal generator, trade simulator, and statutory Indian equities cost model.

### Key Finding
The `SUNPHARMA` trade is **100% mathematically and chronologically reproducible**:
- **Gross Profit:** ₹1,021.2477 (Unrounded)
- **Total Transaction Friction:** ₹42.9324 (Itemized across 6 statutory fee categories)
- **Net Realized Profit:** ₹978.3153 (Unrounded) $\rightarrow$ **₹978.32**
- **Discrepancy with AUDIT-017:** **₹0.00** (Zero variance).

---

## 2. Historical Market Data Verification

The exact daily OHLCV bars stored in `daily_prices` for `SUNPHARMA` (Company ID 51) were extracted:

| Date | Open (₹) | High (₹) | Low (₹) | Close (₹) | Volume | Role in Trade Lifecycle |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **2026-02-26** | 1764.20 | 1792.20 | 1760.30 | 1785.70 | 2,076,586 | Setup formation |
| **2026-02-27** | 1779.00 | 1788.10 | 1730.90 | 1737.00 | 3,041,489 | **Signal Generation Date** |
| **2026-03-02** | 1712.00 | 1759.90 | 1712.00 | 1752.50 | 3,919,270 | **Trade Entry Date** (Next-Day Open) |
| **2026-03-04** | 1721.20 | 1757.20 | 1721.00 | 1750.50 | 4,914,857 | Holding session 1 |
| **2026-03-05** | 1750.00 | 1794.90 | 1748.00 | 1784.50 | 3,600,895 | Holding session 2 |
| **2026-03-06** | 1784.50 | 1805.60 | 1771.80 | 1799.40 | 3,669,921 | Holding session 3 (High near target) |
| **2026-03-09** | 1772.90 | 1815.00 | 1770.00 | 1807.40 | 4,112,775 | **Target Triggered & Exit Date** |

---

## 3. Signal Parameters and Quality Gate Audit

On `2026-02-27`, `run_signal_pipeline("SUNPHARMA", evaluation_date="2026-02-27")` evaluated the stock:

- **Recommendation:** `BUY` (Overall Score: 78.4, Technical Score: 85.0)
- **Point-in-Time Fundamental Data:** 4 quarters eligible (`2025-Q1` through `2025-Q4`); `2026-Q1` was properly excluded as unavailable.
- **Entry Zone:** `[₹1,695.73, ₹1,714.07]`
- **Stop Loss:** `₹1,691.3860`
- **Target Price:** `₹1,806.6000`
- **Risk:** `₹45.6140`
- **Reward:** `₹69.6000`
- **Risk/Reward Ratio:** `1.5258`
- **Quality Gates:** `Passed` (`is_eligible = True`, `risk_reward_ratio >= 1.50`, entry zone valid).

---

## 4. Execution Logic & Position Sizing

1. **Entry Rule (`NEXT_DAY_OPEN`):**
   - Signal generated after market close on Friday `2026-02-27`.
   - Next available trading session: Monday `2026-03-02`.
   - Raw Open Price: **₹1,712.00** (Notice: ₹1,712.00 is strictly inside the entry zone `[₹1,695.73, ₹1,714.07]`).
2. **Slippage Penalty on Entry:**
   - Adverse slippage on Long Entry: $+0.05\%$ ($+0.0005$).
   - Executed Entry Price: $1712.00 \times 1.0005 =$ **₹1,712.8560**.
3. **Position Sizing & Whole-Share Constraint:**
   - Portfolio Capital: ₹100,000.00
   - Maximum Position Allocation: $20.0\% = ₹20,000.00$
   - Target Quantity: $\lfloor \frac{20000.00}{1712.8560} \rfloor = \lfloor 11.676 \rfloor =$ **11 whole shares**.
   - Invested Capital: $11 \times 1712.8560 =$ **₹18,841.4160** (18.84% of portfolio capital).
   - Remaining Cash: $100,000.00 - 18,841.4160 - 22.3501 (\text{entry fees}) =$ **₹81,136.2339**.

---

## 5. Daily Exit Trigger Evaluation

The trade was held across subsequent sessions:
- **2026-03-02:** High ₹1,759.90, Low ₹1,712.00 (within stop/target bounds).
- **2026-03-04:** High ₹1,757.20, Low ₹1,721.00.
- **2026-03-05:** High ₹1,794.90, Low ₹1,748.00.
- **2026-03-06:** High ₹1,805.60, Low ₹1,771.80. Target was ₹1,806.60; high fell short by ₹1.00.
- **2026-03-09:**
  - Session Open: ₹1,772.90
  - Session Low: ₹1,770.00 ($> \text{Stop Loss } ₹1,691.3860$; stop loss NOT triggered).
  - Session High: ₹1,815.00 ($\ge \text{Target } ₹1,806.6000$; **TARGET TRIGGERED**).
  - Same-bar collision rule: Stop loss not breached, so priority rule inactive.
  - Raw Exit Price: $\max(\text{Open}, \text{Target}) = \max(1772.90, 1806.60) =$ **₹1,806.6000**.
4. **Slippage Penalty on Exit:**
   - Adverse slippage on Long Exit: $-0.05\%$ ($-0.0005$).
   - Executed Exit Price: $1806.60 \times (1 - 0.0005) =$ **₹1,805.6967**.

---

## 6. Itemized Statutory & Regulatory Cost Breakdown

Both entry and exit transactions were evaluated against the Indian Equities Delivery schedule:

| Statutory / Fee Component | Rate / Rule Applied | Entry Cost (₹) | Exit Cost (₹) | Total Cost (₹) |
| :--- | :--- | :--- | :--- | :--- |
| **Turnover** | $\text{Price} \times \text{Quantity}$ | ₹18,841.4160 | ₹19,862.6637 | ₹38,704.0797 |
| **Brokerage** | Zero delivery model | ₹0.0000 | ₹0.0000 | ₹0.0000 |
| **Securities Transaction Tax (STT)**| 0.10% on buy & sell delivery | ₹18.8414 | ₹19.8627 | ₹38.7041 |
| **Exchange Transaction (NSE)** | 0.00297% on turnover | ₹0.5596 | ₹0.5899 | ₹1.1495 |
| **SEBI Turnover Fee** | 0.0001% (₹10/crore) | ₹0.0188 | ₹0.0199 | ₹0.0387 |
| **Stamp Duty** | 0.015% on buy turnover only | ₹2.8262 | ₹0.0000 | ₹2.8262 |
| **GST** | 18% on (Brokerage + NSE + SEBI)| ₹0.1041 | ₹0.1098 | ₹0.2139 |
| **Total Transaction Friction** | **Itemized Sum** | **₹22.3501** | **₹20.5823** | **₹42.9324** |

---

## 7. P/L Accounting Reconciliation

$$\text{Gross Realized P/L} = (\text{Exit Price} - \text{Entry Price}) \times \text{Quantity}$$
$$\text{Gross Realized P/L} = (1805.6967 - 1712.8560) \times 11 = 92.8407 \times 11 = \mathbf{₹1,021.2477}$$

$$\text{Total Transaction Costs} = \text{Entry Costs} + \text{Exit Costs} = 22.3501 + 20.5823 = \mathbf{₹42.9324}$$

$$\text{Net Realized P/L} = \text{Gross P/L} - \text{Total Costs} = 1021.2477 - 42.9324 = \mathbf{₹978.3153}$$

$$\text{Trade Net Return} = \frac{\text{Net P/L}}{\text{Invested Capital}} = \frac{978.3153}{18,841.4160} = \mathbf{+5.1924\%}$$

### Portfolio Equity Reconciliation
- Initial Capital: ₹100,000.0000
- Deduct Entry Capital: -₹18,841.4160
- Deduct Entry Costs: -₹22.3501
- Cash after Entry: ₹81,136.2339
- Add Exit Gross Proceeds: +₹19,862.6637
- Deduct Exit Costs: -₹20.5823
- **Final Cash Balance:** **₹100,978.3153** $\rightarrow$ **₹100,978.32**
- Open Position Market Value: ₹0.00
- **Final Portfolio Equity:** **₹100,978.32** (+0.98% net return).

---

## 8. Conclusion

The SUNPHARMA trade reported in AUDIT-017 is an authentic, deterministic outcome of the system's codified rules:
1. Every input, score, entry zone boundary, execution fill, trigger date, and statutory fee was independently computed from scratch.
2. The trade achieved a net profit of ₹978.32 with zero lookahead bias and full transaction cost deductions.
3. Zero mathematical or accounting discrepancies exist.

