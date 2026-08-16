# RSI(14) Technical Engine Validation

## 1. Purpose

This document records the validation of the project's RSI(14) Technical Engine implementation against:
1. Automated unit tests
2. Real project Data Service data
3. TradingView's built-in RSI(14)

The purpose is to verify that the Logic Engineer's RSI implementation produces consistent results before proceeding to the next technical indicator.

## 2. Implementation

Function:

`calculate_rsi(prices, period=14)`

Input:
- pandas Series containing closing prices

Output:
- pandas Series containing RSI values

Calculation:

Delta:
$$\Delta = \text{Close}(t) - \text{Close}(t-1)$$

Gain:
$$\text{Gain} = \max(\Delta, 0)$$

Loss:
$$\text{Loss} = \max(-\Delta, 0)$$

Wilder smoothing:
$$\text{Average Gain} = \text{EWM}(\text{Gain}, \alpha=1/\text{period})$$
$$\text{Average Loss} = \text{EWM}(\text{Loss}, \alpha=1/\text{period})$$

Relative Strength:
$$RS = \frac{\text{Average Gain}}{\text{Average Loss}}$$

RSI:
$$\text{RSI} = 100 - \left(\frac{100}{1 + RS}\right)$$

The implementation uses:
- $\alpha = 1 / \text{period}$
- $\text{period} = 14$
- pandas EWM with `adjust=False`

## 3. Edge Cases

| Scenario | Behavior |
|---|---|
| Insufficient data | NaN values |
| Average Gain = 0 and Average Loss = 0 | RSI = 50 |
| Average Loss = 0 and Average Gain > 0 | RSI = 100 |
| Average Gain = 0 and Average Loss > 0 | RSI = 0 |
| NaN input | NaN preserved appropriately |
| Input mutation | Original input remains unchanged |

## 4. Automated Unit Test Results

Test file:

`backend/engines/tests/test_technical_engine.py`

Result:

9/9 tests passed.

List the tested areas:

1. Increasing/decreasing prices
2. Constant prices
3. Insufficient data
4. NaN handling
5. RSI range 0–100
6. Index preservation
7. Input non-mutation
8. Different RSI periods
9. Invalid inputs

## 5. Data Service Integration Test

RSI was tested using real project data obtained through the existing Data Service.

Stocks tested:

- INFY
- TCS
- WIPRO
- RELIANCE
- HDFCBANK

Result:

Integration test passed.

*Note: The Technical Engine does not directly access the database or yfinance. It consumes the Data Service output.*

## 6. TradingView Manual Validation

TradingView's built-in:

- Relative Strength Index
- Length = 14
- Source = close
- Timeframe = 1D
- Exchange = NSE

Validation date:

14 August 2026

| Stock | Our RSI | TradingView RSI | Absolute Difference |
|---|---:|---:|---:|
| INFY | 58.43 | 58.21 | 0.22 |
| TCS | 52.92 | 52.84 | 0.08 |
| WIPRO | 53.53 | 53.35 | 0.18 |
| RELIANCE | 50.74 | 50.73 | 0.01 |
| HDFCBANK | 33.62 | 33.86 | 0.24 |

Maximum absolute difference: 0.24 RSI points

Average absolute difference: 0.146 RSI points

## 7. Validation Conclusion

RSI(14) has passed:
- Unit testing
- Real Data Service integration testing
- Five-stock TradingView manual validation

The maximum observed difference against TradingView was 0.24 RSI points.

Therefore, RSI(14) is considered validated for the current project phase.

*Note: This validation does NOT mean RSI alone generates a BUY/SELL decision. RSI is only one component of the future Technical Engine and Technical Score.*

## 8. Current Technical Engine Status

| Component | Status |
|---|---|
| RSI(14) | VALIDATED |
| EMA 20 | NOT STARTED |
| EMA 50 | NOT STARTED |
| EMA 200 | NOT STARTED |
| MACD | NOT STARTED |
| ATR | NOT STARTED |
| Support/Resistance | NOT STARTED |
| Volume Analysis | NOT STARTED |
| Technical Score | NOT STARTED |

## 9. Next Step

The next Technical Engine component to implement is EMA 20 / EMA 50 / EMA 200.
