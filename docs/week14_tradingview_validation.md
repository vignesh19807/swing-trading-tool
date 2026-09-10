# Week 14 — TradingView Technical & Signal Validation Report

## 1. Mission & Objective
Validate the Swing Trading Intelligence Platform's technical analysis and signal outputs against external TradingView reference charts across a 15-scenario validation matrix ($5 \text{ stocks} \times 3 \text{ dates}$).

> [!IMPORTANT]
> **Validation Boundary Notice**: TradingView is utilized strictly as a reference/validation benchmark. It does **NOT** replace the project's internal calculation engine, nor are Data Engineer services or core strategy rules altered to force numerical agreement with third-party charts.

---

## 2. 15-Scenario Validation Matrix

| Scenario # | Stock Ticker | Sector | Reference Date | Timeframe | Market Regime Context | Status |
| :---: | :--- | :--- | :---: | :---: | :--- | :---: |
| **1** | `INFY` | IT / Technology | `2025-10-15` | Daily (`1D`) | Sideways / Consolidation | `PENDING` |
| **2** | `INFY` | IT / Technology | `2026-03-13` | Daily (`1D`) | Bearish / Volatile | `PENDING` |
| **3** | `INFY` | IT / Technology | `2026-08-14` | Daily (`1D`) | Bullish Trend | `PENDING` |
| **4** | `TCS` | IT / Technology | `2025-10-15` | Daily (`1D`) | Sideways / Consolidation | `PENDING` |
| **5** | `TCS` | IT / Technology | `2026-03-13` | Daily (`1D`) | Bearish / Volatile | `PENDING` |
| **6** | `TCS` | IT / Technology | `2026-08-14` | Daily (`1D`) | Bullish / Recovery | `PENDING` |
| **7** | `RELIANCE` | Energy / Conglomerate | `2025-10-15` | Daily (`1D`) | Sideways / Rangebound | `PENDING` |
| **8** | `RELIANCE` | Energy / Conglomerate | `2026-03-13` | Daily (`1D`) | Bearish Downtrend | `PENDING` |
| **9** | `RELIANCE` | Energy / Conglomerate | `2026-08-14` | Daily (`1D`) | Bullish / Recovery | `PENDING` |
| **10** | `HDFCBANK` | Financials / Banking | `2025-10-15` | Daily (`1D`) | Sideways / Rangebound | `PENDING` |
| **11** | `HDFCBANK` | Financials / Banking | `2026-03-13` | Daily (`1D`) | Bearish / Volatile | `PENDING` |
| **12** | `HDFCBANK` | Financials / Banking | `2026-08-14` | Daily (`1D`) | Bullish Trend | `PENDING` |
| **13** | `TATASTEEL` | Metals / Cyclical | `2025-10-15` | Daily (`1D`) | Sideways / Consolidation | `PENDING` |
| **14** | `TATASTEEL` | Metals / Cyclical | `2026-03-13` | Daily (`1D`) | Bearish Downtrend | `PENDING` |
| **15** | `TATASTEEL` | Metals / Cyclical | `2026-08-14` | Daily (`1D`) | Bullish / Recovery | `PENDING` |

---

## 3. TradingView Reference Setup Requirements

To maintain scientific validity, manual TradingView observations must be recorded using the following exact configuration:

- **Exchange Tickers**: `NSE:INFY`, `NSE:TCS`, `NSE:RELIANCE`, `NSE:HDFCBANK`, `NSE:TATASTEEL`.
- **Timeframe**: Daily (`1D`).
- **Timezone**: Indian Standard Time (IST / UTC+05:30) / Exchange Time.
- **Price Basis & Data Adjustment**: Use unadjusted/raw price data where available, matching the project's raw close / `auto_adjust=False` basis, and record the exact TradingView data-adjustment setting used.
- **RSI (14)**: Length = 14, Source = `Close`, Smoothing Method = RMA (Wilder's).
- **EMA (20, 50, 200)**: Lengths = 20, 50, 200, Source = `Close`.
- **MACD (12, 26, 9)**: Fast = 12, Slow = 26, Source = `Close`, Signal Length = 9.
- **ATR (14)**: Length = 14, Smoothing Method = RMA (Wilder's).

---

## 4. Methodological Differences & Considerations

### Indicator Warm-up & Historical History Depth
Exponential moving averages (EMA, MACD Signal, Wilder RSI/ATR) rely on recursive decay ($P_t \cdot \alpha + \text{EMA}_{t-1} \cdot (1-\alpha)$). TradingView sessions may load deeper historical bar counts than the database's 500-bar window (~2 years). Minor floating-point differences ($\le 0.05$) due to initial bar warm-up depth are recognized as expected technical behavior.

### Support / Resistance (S/R) Methodology
- **Platform Implementation**: Deterministic 3-bar swing pivot detection (`pivot_window=3`) with 1% zone clustering (`zone_tolerance=0.01`).
- **TradingView Treatment**: TradingView S/R levels (`visual_support`, `visual_resistance`) are captured strictly as visual chart market-structure context. Numerical equivalence against the platform's custom pivot clustering algorithm is **NOT** claimed.

---

## 5. Distinction Between TradingView References & Proprietary Platform Outputs

The validation architecture maintains a strict boundary between input reference observations and proprietary engine outputs:

```
┌─────────────────────────────────────────────────────────┐
│           TRADINGVIEW REFERENCE OBSERVATIONS            │
│  OHLCV, RSI14, EMA20/50/200, MACD (12,26,9), ATR14      │
│  Visual Chart Support / Resistance / Trend              │
└────────────────────────────┬────────────────────────────┘
                             │ (Compared via Tolerances)
                             ▼
┌─────────────────────────────────────────────────────────┐
│            PROPRIETARY PLATFORM OUTPUTS                 │
│  Technical Score (0-100), Recommendation                │
│  Pullback Entry Zone (entry_lower, entry_upper)         │
│  Stop Loss, Target Price, Risk, Reward, Risk/Reward     │
│  Trade Quality Eligibility & Risk Flags                 │
└─────────────────────────────────────────────────────────┘
```

TradingView is **NOT** represented as producing the platform's proprietary scoring, entry-zone, or risk-reward parameters.

---

## 6. Approved Comparison Tolerances

| Parameter Category | Absolute Tolerance | Relative Tolerance | Notes |
| :--- | :---: | :---: | :--- |
| **Categorical / Date / Flags** | Exact Match ($0.0$) | N/A | Must match string/bool values |
| **OHLCV & Price Geometry** | $\pm 0.01$ INR | N/A | Prices, Entry bounds, Stop Loss, Target |
| **Technical Indicators** | $\pm 0.05$ | $\pm 0.1\%$ | RSI, EMA20/50/200, MACD, ATR14 |
| **Composite Scores** | $\pm 0.1$ points | N/A | Technical Score, Opportunity Score |

---

## 7. Discrepancy Classification Rules

1. **`INSUFFICIENT_DATA`**: Automatically assigned when a reference observation value or platform value is `None` or pending.
2. **`ROUNDING_DIFFERENCE`**: Assigned when absolute difference is $< 0.01$ resulting from floating point precision rounding.
3. **`UNRESOLVED`**: Assigned to any unexplained difference exceeding tolerance. Requires systematic manual investigation before reclassifying to `WARMUP_DIFFERENCE`, `PRICE_CONVENTION_DIFFERENCE`, or `IMPLEMENTATION_BUG`.

---

## 8. Point-in-Time Historical Isolation

All historical evaluations strictly enforce point-in-time temporal safety via:
```sql
WHERE c.symbol = ? AND dp.date <= evaluation_date
```
No future candle prices or post-evaluation financial records enter the calculation engine.

---

## 9. Scenario Evidence Table (Initial Pending State)

| Scenario | Symbol | Date | OHLCV Status | RSI(14) | EMA(20) | EMA(50) | EMA(200) | MACD | ATR(14) | Result Status |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| 1 | `INFY` | 2025-10-15 | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` |
| 2 | `INFY` | 2026-03-13 | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` |
| 3 | `INFY` | 2026-08-14 | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` |
| 4 | `TCS` | 2025-10-15 | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` |
| 5 | `TCS` | 2026-03-13 | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` |
| 6 | `TCS` | 2026-08-14 | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` |
| 7 | `RELIANCE` | 2025-10-15 | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` |
| 8 | `RELIANCE` | 2026-03-13 | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` |
| 9 | `RELIANCE` | 2026-08-14 | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` |
| 10 | `HDFCBANK` | 2025-10-15 | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` |
| 11 | `HDFCBANK` | 2026-03-13 | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` |
| 12 | `HDFCBANK` | 2026-08-14 | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` |
| 13 | `TATASTEEL` | 2025-10-15 | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` |
| 14 | `TATASTEEL` | 2026-03-13 | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` |
| 15 | `TATASTEEL` | 2026-08-14 | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` |

*Notice: All values are initialized to `PENDING` awaiting manual chart observation recording.*
