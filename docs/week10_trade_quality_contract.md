# Week 10 — Trade Quality & Risk Flags Contract

## 1. Overview

This document specifies the exact parameters, validation rules, risk flags, risk statuses, and architectural contracts for the Week 10 Trade Quality & Decision Context layer.

---

## 2. Risk / Reward Calculations

The Trade Quality and Signal Engine layers rely on the explicit Week 8 formulas:

- **Pullback-to-Support Entry Zone**:
  - `entry_lower = nearest_support["level"]`
  - `entry_upper = nearest_support["level"] + (atr_14 * 0.50)`
  - *Rule*: `entry_lower <= current_price <= entry_upper`
- **Stop-Loss Methodology**:
  - `stop_loss = nearest_support["zone_low"] - (atr_14 * 1.50)`
  - *Fallback (if support missing)*: `stop_loss = current_price - (atr_14 * 1.50)`
- **Target Methodology**:
  - `target = nearest_resistance["zone_low"]`
  - *Fallback (if resistance missing)*: `target = current_price + (atr_14 * 2.00)`
- **Risk / Reward Metrics**:
  - `risk = current_price - stop_loss`
  - `reward = target - current_price`
  - `risk_reward_ratio = reward / risk`
- **Minimum R:R Threshold**:
  - `MIN_RISK_REWARD_RATIO = 1.50`

---

## 3. Validation Rules & Invalid Reasons

Signal and Trade Quality validation evaluate the setup against the following authoritative reasons:

| Reason String | Trigger Condition | Severity |
| :--- | :--- | :--- |
| `NOT_A_BUY_RECOMMENDATION` | `recommendation != "BUY"` | Ineligible |
| `PRICE_OUTSIDE_ENTRY_ZONE` | `current_price` not in `[entry_lower, entry_upper]` | Ineligible |
| `INSUFFICIENT_RISK_REWARD_RATIO` | `risk_reward_ratio < 1.50` | Ineligible |
| `STOP_ABOVE_CURRENT_PRICE` | `stop_loss >= current_price` | Invalid |
| `INVALID_STRUCTURAL_STOP` | `stop_loss >= nearest_support["zone_low"]` | Invalid |
| `TARGET_BELOW_CURRENT_PRICE` | `target <= current_price` | Invalid |
| `TARGET_BELOW_ENTRY_PRICE` | `target <= entry_price` (`entry_upper`) | Invalid |
| `ENTRY_BELOW_STOP_LOSS` | `entry_upper <= stop_loss` | Invalid |
| `NON_POSITIVE_RISK` | `risk <= 0` | Invalid |
| `NON_POSITIVE_REWARD` | `reward <= 0` | Invalid |
| `MISSING_OR_INVALID_INPUTS` | Required input (`current_price`, `atr_14`, `nearest_support`, `recommendation`) is `None` | Incomplete |
| `INVALID_PAYLOAD` | Signal payload is not a valid `dict` | Invalid |

---

## 4. Trade-Quality Eligibility Rules

A trade setup is marked **ELIGIBLE** (`is_eligible == True`) **ONLY** when:
1. `recommendation == "BUY"`
2. `signal_valid == True` (Signal Engine geometry and R:R >= 1.50 pass)

*Note on Recommendation*: The Decision Engine defines a `BUY` recommendation when Opportunity Score >= 75.0. This threshold belongs strictly to the pre-existing Decision Engine; the Trade Quality Engine does not introduce any new Opportunity Score threshold.

In all other cases, `is_eligible == False`. No additional eligibility criteria or custom score filters are introduced.

---

## 5. Structured Risk Flags

Risk flags provide deterministic explanatory context downstream without modifying Opportunity Scores:

| Flag Name | Triggering Condition | Source Field / Reason | Affects Eligibility? | Affects Score? |
| :--- | :--- | :--- | :--- | :--- |
| `INVALID_PAYLOAD` | Signal payload is not a dict | `type(signal_payload)` | Yes (`is_eligible = False`) | No |
| `NON_BUY_RECOMMENDATION` | `recommendation != "BUY"` | `recommendation` | Yes (`is_eligible = False`) | No |
| `MISSING_INPUTS` | `reason == "MISSING_OR_INVALID_INPUTS"` | `reason`, `missing_inputs` | Yes (`is_eligible = False`) | No |
| `INSUFFICIENT_RISK_REWARD` | `reason == "INSUFFICIENT_RISK_REWARD_RATIO"` | `reason`, `risk_reward_ratio` | Yes (`is_eligible = False`) | No |
| `INVALID_STOP` | `reason` in `STOP_ABOVE_CURRENT_PRICE`, `INVALID_STRUCTURAL_STOP` | `reason` | Yes (`is_eligible = False`) | No |
| `INVALID_TARGET` | `reason` in `TARGET_BELOW_CURRENT_PRICE`, `TARGET_BELOW_ENTRY_PRICE` | `reason` | Yes (`is_eligible = False`) | No |
| `INVALID_RISK` | `reason == "NON_POSITIVE_RISK"` | `reason`, `risk` | Yes (`is_eligible = False`) | No |
| `INVALID_REWARD` | `reason == "NON_POSITIVE_REWARD"` | `reason`, `reward` | Yes (`is_eligible = False`) | No |
| `INVALID_ENTRY` | `reason` in `ENTRY_BELOW_STOP_LOSS`, `PRICE_OUTSIDE_ENTRY_ZONE` | `reason` | Yes (`is_eligible = False`) | No |

---

## 6. Risk Status Categorization

The Trade Quality Engine assigns one of four explicit risk statuses:

- `ELIGIBLE`: Trade setup is a valid BUY recommendation with valid signal geometry and R:R >= 1.50.
- `INELIGIBLE`: Setup has a non-BUY recommendation, fails the entry zone, or yields R:R < 1.50.
- `INVALID`: Setup violates mathematical/structural price bounds (stop above price, target below price, non-positive risk/reward, or invalid payload).
- `INCOMPLETE`: Setup lacks mandatory input parameters (`current_price`, `atr_14`, `nearest_support`).

---

## 7. Missing Data & Data Quality Architecture

- **Data Service**: Provides market and financial data along with `data_quality` flags upstream.
- **Trade Quality Layer**: Does **not** independently reconstruct or enforce `data_quality == "VALID"`. Instead, it relies on the authoritative Signal Engine `reason` and `missing_inputs` output fields.
- **Signal Engine**: Rejects missing inputs deterministically, returning `signal_valid = False`, `reason = "MISSING_OR_INVALID_INPUTS"`, and populating `missing_inputs`.
- **Trade Quality Interpretation**: Maps `reason == "MISSING_OR_INVALID_INPUTS"` to `risk_status = "INCOMPLETE"` and `risk_flags = ["MISSING_INPUTS"]`.

---

## 8. Target Fallback Limitation

**Known Limitation**: The public signal output dictionary (`generate_final_signal`) returns `"target": float | None` but does not expose a `target_type` field. Therefore, downstream consumers cannot deterministically distinguish whether a target was derived from structural resistance or ATR fallback (`current_price + atr_14 * 2.00`).

---

## 9. Historical Evaluation & Date Safety

- **Historical Runs**: Historical evaluations and backtesting runs MUST specify an explicit `evaluation_date` to prevent future data leakage.
- **Pipeline Propagation**: `evaluation_date` propagates through the historical pipeline: `Decision Engine` → `Stop/Target Input Service` → `Signal Engine` → `Trade Quality Engine`.
- **Live Runs**: Current or real-time calls may omit `evaluation_date` (`evaluation_date=None`), utilizing default latest available market data as supported by existing APIs.

---

## 10. Score & Ranking Preservation

Week 10 is strictly additive and preserves all score and ranking logic:
- `technical_score`, `financial_score`, `momentum_score`, `opportunity_score` are **UNTOUCHED**.
- `recommendation` and `final_ranking_score` are **UNTOUCHED**.
- Top 10 ranking order and membership are **UNTOUCHED**.

---

## 11. Top 10 / Eligibility Relationship

- **Ranking Engine**: Ranks Opportunity Scores & Sector Intelligence. Ineligible stocks are **NOT** filtered out of the Top 10 ranking.
- **Trade Quality Context**: Attached additively as context (`stock["trade_quality"]` and `stock["is_eligible"]`) on Top 10 items.

---

## 12. API / UI Output Contract

Public output payload structure:

```json
{
  "symbol": "TCS",
  "evaluation_date": "2026-08-14",
  "recommendation": "BUY",
  "signal_valid": true,
  "entry_lower": 3400.0,
  "entry_upper": 3425.0,
  "stop_loss": 3320.0,
  "target": 3650.0,
  "risk": 80.0,
  "reward": 250.0,
  "risk_reward_ratio": 3.125,
  "reason": "VALID_SIGNAL",
  "missing_inputs": [],
  "is_eligible": true,
  "trade_quality": {
    "is_eligible": true,
    "risk_status": "ELIGIBLE",
    "eligibility_reason": "ELIGIBLE",
    "risk_flags": [],
    "signal_reason": "VALID_SIGNAL",
    "missing_inputs": []
  }
}
```

*Payload Hygiene*: Internal DataFrames (`pd.DataFrame`) and transient calculation contexts (`_explanation_context`) are strictly stripped from public output.

---

## 13. Architecture Boundaries

- **Logic Engineer**: Implements risk formulas, eligibility rules, risk flags, end-to-end integration, and unit tests.
- **Data Engineer**: Manages SQLite database, data collection, validation, and input services (`stop_target_input_service`).
- **UI Engineer**: Consumes structured API payloads. (No UI work performed in Week 10).
- **Strict Constraints**: No direct DB access in logic engines, no external API/`yfinance` calls, no indicator recalculation in Trade Quality.

---

## 14. Known Limitations

1. **Target Fallback Source Not Exposed**: The public signal contract does not specify whether target came from structural resistance or ATR multiplier.
2. **Top 10 Signal Context Re-evaluation**: `rank_universe` invokes `run_signal_pipeline` post-ranking for Top 10 items to fetch trade quality context.
3. **Data Quality Representation**: Data Service handles `data_quality` upstream; Trade Quality interprets missing values via Signal Engine `missing_inputs`.

---

## 15. Test Coverage & Execution Results

All 73 unit and integration tests executed cleanly:

```powershell
python -m unittest backend/logic/test_trade_quality_engine.py backend/logic/test_signal_engine.py backend/logic/test_signal_integration.py backend/logic/test_end_to_end_integration.py backend/engines/test_ranking_engine.py backend/engines/test_universe_orchestrator.py
```

Result: `Ran 73 tests in 1.187s - OK`.
