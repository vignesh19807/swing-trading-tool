# Week 8 Signal Rules Specification

## V1 Signal Engine Parameters

The following project-level parameters have been approved for the initial V1 Signal Engine implementation.
These parameters govern the exact thresholds for entry zones, stop losses, and targets.

- **ENTRY_MULTIPLIER = 0.50**
  *Rationale:* Provides a balanced pullback-to-support entry zone, ensuring price is close enough to support without being excessively restrictive.
- **STOP_MULTIPLIER = 1.50**
  *Rationale:* Provides reasonable ATR-based protection against normal daily volatility while maintaining tight structural risk controls.
- **TARGET_MULTIPLIER = 2.00**
  *Rationale:* Provides a practical momentum-based profit-taking fallback when no valid overhead structural resistance exists.
- **MIN_RISK_REWARD_RATIO = 1.50**
  *Rationale:* Ensures a mathematically sound minimum trade-quality filter for positive expectancy without overly restricting the universe of tradable setups.

*(Note: These are the explicit Signal Engine parameters. They supersede and are distinct from any default parameters in the Data Engineer input services.)*

---

## Signal Eligibility Rules

A long trading setup is only considered **VALID** if it meets the following strict criteria:
1. **Decision Engine Approval:** `recommendation == "BUY"` (i.e. Opportunity Score >= 75).
2. **Data Quality:** The Data Engineer input services must return `data_quality == "VALID"` (no required inputs can be missing).
3. **Entry Criteria:** `current_price` must be within the defined Pullback-to-Support Entry Zone.
4. **Risk/Reward Criteria:** The setup must yield a `risk_reward_ratio >= MIN_RISK_REWARD_RATIO` (1.50).
5. **Logic Validation:** `target > current_price`, `target > entry`, and `entry > stop_loss`.

---

## Methodologies & Formulas

### 1. Pullback-to-Support Entry Zone
The stock must be structurally a "BUY" and currently trading within a low-risk accumulation zone just above a valid support level.

- **Lower Bound:** `nearest_support["level"]`
- **Upper Bound:** `nearest_support["level"] + (atr_14 * ENTRY_MULTIPLIER)`
- **Rule:** Valid only when `current_price >= lower_bound` AND `current_price <= upper_bound`.

### 2. Stop-Loss Methodology
An ATR-padded structural stop placed below the nearest valid support level to avoid false triggers from noise.

- **Primary Formula:** `stop_loss = nearest_support["zone_low"] - (atr_14 * STOP_MULTIPLIER)`
- **Validation:** `stop_loss < current_price` AND `stop_loss < nearest_support["zone_low"]`.
- **Fallback:** (If structural support is unavailable): `stop_loss = current_price - (atr_14 * STOP_MULTIPLIER)`.

### 3. Target Methodology
Take profit near the closest overhead structural supply zone.

- **Primary Formula:** `target = nearest_resistance["zone_low"]`
- **Fallback:** (If no valid overhead resistance exists, e.g., all-time highs): `target = current_price + (atr_14 * TARGET_MULTIPLIER)`.

### 4. Risk / Reward Calculation
- **Risk:** `risk = current_price - stop_loss`
- **Reward:** `reward = target - current_price`
- **Risk/Reward Ratio:** `risk_reward_ratio = reward / risk`
- **Validation:** `risk > 0`, `reward > 0`, `risk_reward_ratio > 0`.

---

## Missing-Data Behavior
The Logic/Risk Engine operates deterministically:
- It **WILL NOT** silently invent, fabricate, or forward-fill missing data.
- If a required input (e.g., `current_price`, `atr_14`, `nearest_support`) is missing, the setup is strictly **REJECTED** and marked as INVALID.
- The `reason` field in the explainable signal output will clearly indicate which input was missing.

---

## Evaluation-Date Requirement (Historical Backtesting)
The Data Engineer input services (`entry_exit_input_service.py` and `stop_target_input_service.py`) must be strictly **evaluation-date safe**.
- **Historical Runs:** When an `evaluation_date` is provided, the data pipeline strictly bounds all SQL queries to that exact date, preventing any future data from leaking into the entry/exit, support/resistance, or ATR logic.
- **Live Runs:** If `evaluation_date` is `None`, the services continue to default to the latest available real-time or end-of-day market data.

---

## Architectural Separation of Concerns
There is a strict boundary between the Data Engineer layer and the Logic/Risk layer:
- **Data Engineer Services:** Provide raw market data, valid support/resistance structures, and standard technical inputs. They **do not** generate BUY/SELL signals, qualify trades, or apply risk minimums.
- **Logic Engine / Signal Engine:** Consumes standard inputs and applies the exact formulas and rules defined in this document. It **does not** query SQLite directly, execute raw SQL, invoke `yfinance`, or recalculate technical indicators.
