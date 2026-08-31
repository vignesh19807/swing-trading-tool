# Sector & Industry Intelligence Engine Contract

## 1. Purpose
The Sector & Industry Intelligence Engine is responsible for calculating historical performance and relative strength for sectors and industries based on their constituent stocks. It translates raw Data Engineering feeds into highly structured metrics that downstream logic layers (like ranking algorithms and opportunity score models) can consume.

## 2. Architecture Boundary
The Logic Engine maintains strict separation of concerns from the Data Pipeline.
- **NO** direct SQLite access.
- **NO** `yfinance` usage or external scraping.
- **NO** database schema changes.
- Consumes clean, normalized data entirely via the Data Engineer python service boundaries.

```
Logic Engine
    ↓
Data Pipeline services
    ↓
historical/classification data
    ↓
sector/industry calculations
    ↓
structured output
```

## 3. Data Engineer Dependencies
The engine relies on the following read-only interfaces:
- `backend.data_pipeline.classification_service`: For fetching sector constituents, industry constituents, and validating company classifications.
- `backend.data_pipeline.historical_data_service`: For retrieving historical OHLCV data using `get_historical_data`.

## 4. Sector Input
Function: `evaluate_sector(sector: str, evaluation_date: str = None, lookback_periods: list[int] = None)`
- **`sector`**: Exact string matching the sector name in the database.
- **`evaluation_date`**: ISO format date string (e.g. `2026-08-31`) to enforce determinism in historical retrieval. If None, the latest available data is used.
- **`lookback_periods`**: Defines the periods over which to calculate returns. Defaults to `[21, 63, 126, 252]`.

## 5. Industry Input
Function: `evaluate_industry(industry: str, evaluation_date: str = None, lookback_periods: list[int] = None)`
- Mirrors the sector interface exactly, but queries industry classifications.

## 6. Historical Return Calculation
Return is calculated using the formula:
```
return = (latest_price / historical_price) - 1
```
- The "latest price" is the closing price on or just before the `evaluation_date`.
- The "historical price" is exactly `N` trading days before the latest price observation within the retrieved dataset.
- `adjusted_close` is prioritized; if missing, falls back to `close`.
- Handles NaN, <= 0.0 starting prices, and insufficient history gracefully by excluding the constituent for that specific period.

## 7. Lookback Periods
The default trading-day lookback periods are:
- **21D**: 1 Month
- **63D**: 3 Months
- **126D**: 6 Months
- **252D**: 1 Year

*(Calendar days are not used to index historical data).*

## 8. Aggregation Method
Sector and Industry performance is an **equal-weighted average** of the valid constituent returns for each period.
If `INFY` is +20% and `TCS` is +10%, the sector return is +15%.

## 9. Missing-Data Behavior
- **Constituents**: If a stock has data for 21D but not 252D, it is included in the 21D average but excluded from the 252D average.
- **No Conversion to Zero**: Missing returns are **never** treated as 0.0. They are simply excluded from the mean.
- **Group Insufficiency**: If zero constituents have valid data for a given period, the aggregate performance for that period is `None`.
- Explicit warnings and missing stock lists are reported in `data_quality`.

## 10. Relative-Strength Behavior
Relative strength against the broader market is currently calculated against the `NIFTY_50` benchmark, representing sector/industry outperformance or underperformance.

- **Formula**: `relative_strength = group_return - benchmark_return`. The output is expressed in percentage points (e.g., +4% means the sector outperformed the benchmark by 4 percentage points).
- **Periods**: Calculated individually across `21D`, `63D`, `126D`, and `252D` matching the group evaluation ranges.
- **Missing Benchmark Behavior**: If the Data Engineer's benchmark historical service returns no data for a given period, or if the service does not exist, the relative strength for that period defaults to `None`.
- **Unavailable Status**: If the entire benchmark is unavailable, `status` resolves to `UNAVAILABLE` and an explicit `warning` is attached. If only some periods are missing, it resolves to `PARTIAL`.

*Note: Since there is currently no benchmark tracking in the SQLite database, this is fully prepared but returns `UNAVAILABLE` in production until the Data Engineers fulfill the dependency.*

## 11. Evaluation-Date Behavior
When `evaluation_date` is supplied, the engine passes it down to `get_historical_data(end_date=evaluation_date)`. This guarantees determinism, so running the engine on historical dates yields mathematically reproducible outcomes.

## 12. Output Contract
The standard output is a fully defined JSON-like dictionary:
```python
{
    "sector": "Information Technology",
    "evaluation_date": "2026-08-31",
    "constituents_count": 5,
    "constituents": ["INFY", "TCS", "WIPRO", ...],
    "performance": {
        "21D": 0.045,
        "63D": 0.082,
        "126D": 0.154,
        "252D": 0.221
    },
    "relative_strength": {
        "benchmark": "NIFTY_50",
        "status": "UNAVAILABLE",
        "21D_rs": None,
        "63D_rs": None,
        "126D_rs": None,
        "252D_rs": None,
        "warning": "Benchmark historical data service is not currently available."
    },
    "data_quality": {
        "status": "VALID", # or PARTIAL or INSUFFICIENT_DATA
        "missing_stocks": [],
        "warnings": []
    }
}
```

## 13. Benchmark Dependency / Blocker
**Blocker**: The Data Pipeline currently lacks a service and historical database tables for benchmark/index data (e.g. NIFTY 50).
The Logic Engine has successfully built the deterministic `_rs` calculation architecture, but it will safely return `UNAVAILABLE` rather than fabricating live market data.

## 14. Future Integration Point
Once a benchmark service (`get_benchmark_historical_data`) is exposed by the Data Engineer, the Logic Engine will automatically calculate valid relative strength by consuming it identically to stock constituents.

## 15. Sector Ranking Methodology
Function: `rank_sectors(sectors: List[str], evaluation_date: str = None, ranking_period: str = "63D")`
(Also available for industries: `rank_industries`)

- **Performance Calculation**: Iterates through the provided list of sectors, invoking `evaluate_sector()` for each to obtain its deterministic performance and constituent data quality.
- **Aggregation Rule**: Uses the exact equal-weighted logic defined in the evaluation phase, respecting missing stock exclusions.
- **Ranking Rule**: Sectors are primarily ordered by their aggregate `performance` for the specified `ranking_period` in descending order (highest performance is ranked 1).
- **Tie Handling**: If multiple sectors have the exact same performance value, a deterministic secondary sort is applied using alphabetical order of the sector name.
- **Incomplete-Data Handling**: Missing constituents within a sector are reported in `data_quality.missing_stocks` and `valid_constituents_count`. The sector is still ranked using its valid constituents as long as at least one exists.
- **Insufficient-Data Behavior**: If a sector has zero valid constituents for the `ranking_period`, its performance is `None`. These sectors are explicitly placed at the end of the ranking array, assigned a `rank` of `None`, and carry an `INSUFFICIENT_DATA` data quality status.
- **Deterministic/Reproducibility Rules**: Since the underlying `evaluate_sector` enforces an optional `evaluation_date` and sorts deterministically, `rank_sectors` is 100% mathematically reproducible for any historical date.
- **Known Limitations**: Ranking requires data for the target period. It currently does not factor in volatility, drawdown, or benchmark relative strength.

## 16. Industry Ranking Methodology
Function: `rank_industries(industries: List[str], evaluation_date: str = None, ranking_period: str = "63D")`

- **Constituent Aggregation**: Identical to sector ranking, it leverages `evaluate_industry()` which equal-weights valid constituent stock returns.
- **Return Calculation**: Calculated precisely as `(latest_price / historical_price) - 1.0` using trading-day lookbacks, preserving non-zero handling for missing price data.
- **Ranking Order**: Industries with sufficient data are primarily sorted by aggregate `performance` in descending order.
- **Tie-Breaking**: If two or more industries share an identical performance value, a deterministic alphabetical secondary sort is applied to the industry name (ascending).
- **Missing-Data Behavior**: Missing constituents do NOT silently convert to 0%. The valid constituents simply dominate the average, and the missing stocks are logged within `data_quality.missing_stocks` and `valid_constituents_count`.
- **Insufficient-Data Behavior**: If an industry contains zero valid constituents for the `ranking_period`, it yields `None` performance. These industries are explicitly demoted to the bottom of the array with `rank: None` and a status of `INSUFFICIENT_DATA`.
- **Deterministic Behavior**: The sorting algorithm is stable and purely deterministic. The optional `evaluation_date` enables exact reproducibility.
- **Known Limitations**: As with sector ranking, relative strength comparisons against a benchmark are blocked pending a benchmark data service.

## 17. Preliminary Sector/Industry Score Methodology
A preliminary score is calculated dynamically during evaluation to numerically represent raw foundational performance.

- **Score Range**: Strictly normalized and clamped to `0.0` (minimum) to `100.0` (maximum).
- **Input Factors**: The score leverages two distinct performance lookbacks:
  - `21D` (Short term)
  - `63D` (Medium term)
- **Formula**: `Score = 50.0 + clamp(21D_return * 100, -25, 25) + clamp(63D_return * 100, -25, 25)`
- **Weights & Normalization**: The score begins at a neutral `50.0`. Each 1% of positive return adds +1 point (up to a max of +25 points per period). Each 1% of negative return subtracts -1 point (up to a max of -25 points per period). This guarantees a maximum possible score of exactly 100.0 and a minimum of 0.0.
- **Missing-Input Behavior**: If one period is missing, its component resolves to `0.0` (neutral impact) but the score is still computed. If both inputs are entirely missing, the preliminary score evaluates to `None`.
- **Explainability**: The output dictionary nested under `preliminary_score` explicitly breaks down the calculation for full transparency:
  - `score`: The final normalized score.
  - `range`: Fixed min/max dictionary.
  - `components`: Dict tracking the `base`, `21D_component`, and `63D_component` values.
- **Known Limitations**: This score solely represents raw performance momentum. It does not factor in volatility, volume, macro conditions, or benchmark-relative strength.

## 18. Sector/Industry Engine Orchestrator
The top-level execution module is located at `backend/engines/sector_industry_engine.py` using `run_sector_industry_engine()`.

**Data Flow**:
1. Engine calls `backend.data_pipeline.classification_service` (`get_sectors`, `get_industries`) to discover the universe.
2. It orchestrates calls to the Logic layer (`rank_sectors`, `rank_industries`).
3. Logic layer pulls historical data from `backend.data_pipeline.historical_data_service` and computes relative strength / scores.
4. Engine packages all logic results into a single consolidated JSON report.

**Assumptions**:
- All upstream components are successfully populated in the SQLite database by the Data Engineer pipeline.
- Evaluation dates match market trading days.

**Engine Input Contract**:
```python
def run_sector_industry_engine(
    evaluation_date: Optional[str] = None,
    ranking_period: str = "63D"
) -> Dict[str, Any]:
```

**Engine Output Contract**:
```json
{
  "status": "VALID" | "PARTIAL" | "INSUFFICIENT_DATA",
  "evaluation_date": "2025-10-10",
  "ranking_period": "63D",
  "sectors_analyzed": 4,
  "industries_analyzed": 12,
  "sector_rankings": [
    {
      "rank": 1,
      "sector": "Banking",
      "performance": 0.30,
      "relative_strength": { ... },
      "preliminary_score": { ... },
      "constituents_count": 15,
      "valid_constituents_count": 15,
      "data_quality": "VALID",
      "warnings": []
    }
  ],
  "industry_rankings": [ ... ]
}
```

## 19. Friday Integration Notes
- The orchestrator completes the Logic Engineer's Week 5 domain.
- The `sector_industry_engine.py` file exposes relative strength, data-quality cascades, rankings, and scoring out-of-the-box.
- **Benchmark Limitation Maintained**: The orchestrator strictly delegates benchmark resolution to the logic layer, meaning it securely forwards the `UNAVAILABLE` tag up the stack without triggering crashes or requiring schema redesigns.

## 20. Week 6 Monday: Stock Context Analyzer
The Stock Context Analyzer (`backend/logic/stock_context_analyzer.py`) bridges an individual stock symbol to its sector and industry via the `classification_service`.

**Purpose**: Fetches the sector and industry mapped to a single stock symbol.
**Data Engineer Dependency**: Strictly consumes `get_company_classification` from `backend.data_pipeline.classification_service`.
**Architecture Boundary**: No SQLite, no raw SQL, no external APIs.

**Input**:
`get_stock_context(symbol: str) -> dict`

**Output Contract (Valid Symbol)**:
```json
{
    "symbol": "INFY",
    "status": "VALID",
    "company_name": "Infosys Limited",
    "sector": "Information Technology",
    "industry": "IT Services"
}
```

**Output Contract (Missing Symbol)**:
If a symbol is unknown, empty, or whitespace, it safely defaults to:
```json
{
    "symbol": "UNKNOWN_TICKER",
    "status": "NOT_FOUND",
    "company_name": null,
    "sector": null,
    "industry": null
}
```

## 21. Week 6 Tuesday: Sector-Filtered Stocks
Building on the Stock Context Analyzer, this module allows retrieving context for an entire sector or industry grouping.

**Purpose**: Fetches the structured stock context array for all constituents of a specified sector or industry.
**Data Engineer Dependency**: Consumes `get_sector_stocks` and `get_industry_stocks` from `backend.data_pipeline.classification_service`.
**Architecture Boundary**: No SQLite, no raw SQL, no external APIs.

**Inputs**:
`get_sector_contexts(sector: str) -> list[dict]`
`get_industry_contexts(industry: str) -> list[dict]`

**Output Contract (Valid Filter)**:
```json
[
  {
      "symbol": "INFY",
      "status": "VALID",
      "company_name": "Infosys Limited",
      "sector": "Information Technology",
      "industry": "IT Services"
  },
  {
      "symbol": "TCS",
      "status": "VALID",
      "company_name": "Tata Consultancy Services Limited",
      "sector": "Information Technology",
      "industry": "IT Services"
  }
]
```

**Missing-Filter Behavior**:
If the provided sector or industry is unknown, empty string `""`, `None`, or whitespace, the Data Engineer correctly returns `[]`. The filtering functions pass this deterministic property on, returning an empty list `[]` without error.

## 22. Week 6 Wednesday: Sector Performance Context
Combines the individual stock's momentum returns alongside its Sector's aggregated average returns and scores to facilitate comparative outperformance/underperformance analysis.

**Purpose**: Unifies an individual stock's performance with its overarching Sector context up to a specified evaluation date.
**Data Engineer Dependency**: Reuses Week 5's `evaluate_sector` engine recursively and aliases `_calculate_constituent_returns` to fetch the individual stock's math.
**Architecture Boundary**: No SQLite, no raw SQL, no external APIs.

**Input**:
`get_stock_sector_performance_context(symbol: str, evaluation_date: Optional[str] = None, lookback_periods: Optional[List[int]] = None) -> dict`

**Output Contract**:
```json
{
    "symbol": "INFY",
    "evaluation_date": "2025-10-10",
    "status": "VALID",
    "classification": {
        "company_name": "Infosys Limited",
        "sector": "Information Technology",
        "industry": "IT Services"
    },
    "stock_performance": {
        "21D": 0.05,
        "63D": 0.12
    },
    "sector_performance": {
        "data_quality": "VALID",
        "performance": {
            "21D": 0.04,
            "63D": 0.10
        },
        "preliminary_score": {
            "score": 85.0
        },
        "relative_strength": {
            "status": "UNAVAILABLE"
        }
    }
}
```

**Missing/Invalid Behavior**:
If the stock symbol is entirely unknown, the function safely defaults `stock_performance` and `sector_performance` to `null` while preserving the `NOT_FOUND` base status, ensuring consumers do not crash when accessing missing metrics.

## 23. Week 6 Thursday: Decision Engine Integration
The Decision Engine orchestrates the final composite Opportunity Score. Sector Intelligence is seamlessly injected directly into this logic.

**Producer Workflow**: The caller/orchestrator evaluates `get_stock_sector_performance_context` and passes the resulting payload untouched into `calculate_opportunity_score`. The Decision Engine performs zero duplicate calculations or Data Pipeline historical fetching for the sector logic.

**Backward Compatibility**: The Sector Intelligence payload strictly acts as an **overlay**. It does not alter Technical, Financial, or Momentum weighting in V1, nor does its absence degrade the overarching evaluation status or recommendation calculations.

**Input Modification**:
```python
def calculate_opportunity_score(
    symbol: str,
    evaluation_date: Optional[str] = None,
    sector_intelligence: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
```

**Output Contract Format**:
```json
{
    "symbol": "INFY",
    "status": "VALID",
    "technical_score": 75.0,
    "financial_score": 80.0,
    "momentum_score": 70.0,
    "opportunity_score": 75.0,
    "recommendation": "BUY",
    "sector_intelligence": {
        "symbol": "INFY",
        "evaluation_date": "2025-10-10",
        "status": "VALID",
        "classification": { ... },
        "stock_performance": { ... },
        "sector_performance": { ... }
    }
}
```

**Missing Data**:
If no intelligence is passed, the Decision Engine deterministically sets `"sector_intelligence": null`.

## 24. Week 7 Tuesday: Ranking Engine (Top 10)
The Ranking Engine is a pure transformation layer that sits above the Decision Engine. It ingests an array of unmodified Decision Engine outputs, applies Sector Intelligence as a macroeconomic overlay, and yields the final sorted Top 10 stocks.

**Ranking Formula**:
```python
final_ranking_score = (opportunity_score * 0.70) + (sector_score * 0.30)
```

**Missing Data / Fallback Strategy**:
- If `sector_intelligence` or the scalar `preliminary_score.score` is absent, the engine defaults `sector_score = opportunity_score`. This preserves the stock's intrinsic rating and treats the sector overlay as completely neutral.
- If the core `opportunity_score` is missing or the stock status is `INSUFFICIENT`, the stock is fundamentally unrankable.

**Tie-Breaking**:
If two stocks have an identical `final_ranking_score`, ties are broken deterministically:
1. `opportunity_score` (Descending)
2. `symbol` (Ascending / Alphabetical)

**Output Contract Format**:
```json
{
    "evaluation_date": "2026-08-14",
    "top_10": [
        {
            "rank": 1,
            "symbol": "TCS",
            "final_ranking_score": 79.4,
            "opportunity_score": 77.0,
            "sector_score": 85.0,
            "recommendation": "BUY",
            "sector": "Information Technology",
            "industry": "IT Services",
            "status": "VALID"
        }
    ],
    "unranked": [
        {
            "symbol": "ABC",
            "status": "VALID",
            "reason": "OUTSIDE_TOP_10"
        },
        {
            "symbol": "XYZ",
            "status": "INSUFFICIENT",
            "reason": "MISSING_CORE_OPPORTUNITY_SCORE"
        }
    ]
}
```


## 25. Week 7 Friday: Universe Orchestrator
The final layer of the Logic Engine sits at ackend/engines/universe_orchestrator.py via the
ank_universe(evaluation_date=None) function.

**Purpose**: Coordinates the entire Data Pipeline universe through the Decision Engine and into the Ranking Engine without duplicating logic.

- **Data Boundary**: Automatically infers the valid stock universe dynamically via ackend.data_pipeline.classification_service.get_all_classifications().
- **Failure Isolation**: Explicitly wraps each stock's sector fetch and Decision Engine calculation in a 	ry/except block. A data-quality crash on an individual stock simply yields an INSUFFICIENT tag, preventing one bad ticker from collapsing the entire Top 10 run.
- **Pure Orchestration**: The orchestrator strictly passes dicts. It performs no yfinance fetches, executes no SQL, and contains zero mathematical ranking or weighting logic.
- **Determinism**: The evaluation_date is faithfully passed downward into the Sector context, Decision context, and Ranking context simultaneously, ensuring full point-in-time accuracy.
