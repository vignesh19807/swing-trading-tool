# DATA PROVENANCE AND LIMITATIONS
**Swing Trading Intelligence Platform — Indian Equities**  
**Document Revision:** 1.0.0 (AUDIT-036 Release Final)  
**Date:** 2026-10-30  

---

## 1. Data Sources & Ingestion Provenance

The platform relies on two primary data streams stored locally in SQLite (`database/swing_trading.db`):

| Data Stream | Primary Provider | Local Table | Coverage | Quality Status |
| :--- | :--- | :--- | :--- | :--- |
| **Daily OHLCV Bars** | Yahoo Finance (`yfinance`) | `daily_prices` | 52 Equities, 496 Trading Days (2024-10-23 to 2026-10-23), 25,746 bars | **100% Validated** (Zero geometric errors, zero negative volume, zero inverted bounds). |
| **Technical Indicators** | Local Pipeline Engine | `technical_indicators` | 25,746 rows (RSI-14, MACD, EMA-20/50/200, ATR-14) | **100% Validated** (Nulls strictly confined to mathematical warmup windows). |
| **Quarterly Financials** | Corporate Filings / Historical Extractor | `quarterly_results` | 52 Equities, 5 Quarters (2025-Q1 to 2026-Q1), 260 quarterly rows | **Point-in-Time Safe via Conservative Fallback Lag**. |

---

## 2. Critical Financial Data Limitation: Missing Publication Dates

### The Issue:
All **260 records** in `quarterly_results` currently have `publication_date = NULL`. Regulatory disclosure timestamps from the National Stock Exchange (NSE) / BSE corporate announcements API were not captured in the raw historical dataset.

### The Point-in-Time Safeguard:
To prevent severe lookahead bias (evaluating a trading decision using earnings that had not yet been released to the public):
1. Under SEBI regulations (LODR), listed Indian corporations are granted **45 calendar days** following the end of a financial quarter to declare un-audited quarterly results.
2. In `financial_service.py` and across all 7 fundamental analyzers, whenever `publication_date` is `NULL`, the engine enforces a **strict 45-day conservative calendar lag**:
   $$\text{Earliest Availability Date} = \text{Quarter End Date} + 45\text{ days}$$
3. For example:
   - Quarter `2025-Q1` (Quarter ending 2025-03-31): Results become legally available on **2025-05-15**.
   - Before 2025-05-15, all quarterly financial queries for `2025-Q1` return `NO_ELIGIBLE_RECORDS`, completely immunizing the system against lookahead leakage.
4. **Residual Risk:**
   While the 45-day fallback prevents lookahead bias, it introduces a **reporting lag bias** for companies that report early (e.g. within 15–20 days). Upgrading the ingestion pipeline to fetch exact SEBI corporate announcement timestamps from NSE India is recommended for future releases.

---

## 3. Stock Universe Coverage: 52 Equities vs. 100-Stock Target

### Universe Profile:
- **Current Store:** 52 equities
  - 50 Nifty 50 constituents (e.g., RELIANCE, TCS, INFY, HDFCBANK, SUNPHARMA).
  - 2 Nifty Next 50 constituents (`ABB`, `ADANIENSOL`).
  - 2 Demerged / Spinoff tickers (`ETERNAL`, `TMPV`).
- **Expansion Target:** Nifty 100 Index.
- **Coverage Status:**
  To achieve full Nifty 100 coverage, an additional **48 Nifty Next 50 tickers** must be ingested.
  Historical price and quarterly records for these 48 tickers have not yet been downloaded to prevent unverified data pollution during the audit sequence.

---

## 4. Survivorship Bias & Index Membership

1. **Current Index Membership:**
   The historical dataset evaluates the *current* constituents of the Nifty 50 over the historical span (2024 to 2026).
2. **Survivorship Bias Consideration:**
   Stocks that were excluded from the index or liquidated during earlier periods are not represented. While this has negligible impact on short-term swing trading setups (holding period 5–20 days), researchers should note that long-term multi-year buy-and-hold comparisons inherit mild survivorship bias.

---

## 5. Summary of System Limitations

1. **Trade Frequency:** The platform's risk filters reject 99.4% of raw signals, producing an average of ~0.4 trades per month across the 52-stock universe.
2. **Execution Assumptions:** Backtesting assumes whole-share execution at Day $T+1$ Open with 10 bps slippage and Zerodha delivery statutory charges. Real-world fill prices may diverge during extreme gap openings or market circuit freezes.
3. **Index Benchmark:** Local store does not contain a traded index ETF series (e.g., NIFTYBEES); market breadth is derived cross-sectionally from the 52 constituent stocks.

