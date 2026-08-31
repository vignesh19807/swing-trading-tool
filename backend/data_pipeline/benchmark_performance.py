"""
Week 15 - Performance and Scalability Benchmark
================================================

Measures query execution times, row throughput, and latency across core
Data Engineering services for the Swing Trading Intelligence Platform.

Evaluates:
1. Single-stock OHLCV retrieval (get_stock_data)
2. Latest price lookup (get_latest_price)
3. Historical date range retrieval (get_stock_data over 1 year)
4. Multi-stock 50-universe batch extraction (all 50 stocks)
5. Technical indicator retrieval (get_technical_indicators)
6. Financial data retrieval (get_financial_data & get_latest_financial_data)
7. Backtest input extraction (get_backtest_inputs)
8. Backtest result persistence & retrieval (store_backtest_results & get_backtest_results)
9. Database Index review & EXPLAIN QUERY PLAN verification

Data Engineer boundary:
- Measures data access performance.
- Verifies index utilization.
- Does not modify trading strategy or scoring logic.
"""

import json
import os
import sys
import sqlite3
import time
import tracemalloc
from pathlib import Path
from typing import Any, Callable, Dict, List, Tuple

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import pandas as pd

from backend.data_pipeline.data_service import (
    get_available_stocks,
    get_latest_price,
    get_stock_data,
    get_stock_record_count,
)
from backend.data_pipeline.historical_data_service import get_historical_data
from backend.data_pipeline.technical_indicator_service import (
    get_latest_technical_indicators,
    get_technical_indicators,
)
from backend.data_pipeline.financial_service import (
    get_financial_data,
    get_financial_stocks,
    get_latest_financial_data,
)
from backend.data_pipeline.classification_service import get_company_classification
from backend.data_pipeline.backtest_data_access_service import (
    get_backtest_input,
    get_backtest_inputs,
)
from backend.data_pipeline.backtest_result_service import (
    get_backtest_results,
    store_backtest_result,
    store_backtest_results,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATABASE_PATH = PROJECT_ROOT / "database" / "swing_trading.db"
REPORTS_DIR = PROJECT_ROOT / "reports"
REPORTS_DIR.mkdir(exist_ok=True)


def time_operation(
    name: str,
    func: Callable[[], Any],
    iterations: int = 5,
) -> Dict[str, Any]:
    """
    Measure execution time (avg, min, max ms), memory, and row count.
    """
    times_ms: List[float] = []
    result = None

    tracemalloc.start()
    start_mem, _ = tracemalloc.get_traced_memory()

    for _ in range(iterations):
        t0 = time.perf_counter()
        result = func()
        t1 = time.perf_counter()
        times_ms.append((t1 - t0) * 1000.0)

    _, peak_mem = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    avg_ms = sum(times_ms) / len(times_ms)
    min_ms = min(times_ms)
    max_ms = max(times_ms)

    row_count = 0
    if isinstance(result, pd.DataFrame):
        row_count = len(result)
    elif isinstance(result, list):
        row_count = len(result)
    elif isinstance(result, dict):
        row_count = 1 if result else 0
    elif isinstance(result, int):
        row_count = result

    return {
        "operation": name,
        "iterations": iterations,
        "avg_ms": round(avg_ms, 3),
        "min_ms": round(min_ms, 3),
        "max_ms": round(max_ms, 3),
        "row_count": row_count,
        "peak_memory_kb": round(peak_mem / 1024.0, 2),
    }


def review_database_indexes() -> List[Dict[str, str]]:
    """
    Inspect all existing indexes and query plans for core query patterns.
    """
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()

    index_rows = cursor.execute(
        """
        SELECT name, tbl_name, sql
        FROM sqlite_master
        WHERE type = 'index' AND name NOT LIKE 'sqlite_%'
        ORDER BY tbl_name, name
        """
    ).fetchall()

    indexes = [
        {"name": row[0], "table": row[1], "sql": row[2] or "PRIMARY/UNIQUE"}
        for row in index_rows
    ]

    # Test key query plans with EXPLAIN QUERY PLAN
    query_plans = {}

    queries = {
        "daily_prices_by_symbol_and_date": """
            EXPLAIN QUERY PLAN
            SELECT dp.date, dp.open, dp.high, dp.low, dp.close, dp.volume
            FROM daily_prices dp
            JOIN companies c ON c.id = dp.company_id
            WHERE c.symbol = 'INFY' AND dp.date >= '2025-01-01'
            ORDER BY dp.date ASC
        """,
        "technical_indicators_by_symbol": """
            EXPLAIN QUERY PLAN
            SELECT ti.*
            FROM technical_indicators ti
            JOIN companies c ON c.id = ti.company_id
            WHERE c.symbol = 'INFY'
            ORDER BY ti.date ASC
        """,
        "quarterly_results_by_symbol": """
            EXPLAIN QUERY PLAN
            SELECT qr.*
            FROM quarterly_results qr
            JOIN companies c ON c.id = qr.company_id
            WHERE c.symbol = 'INFY'
            ORDER BY qr.quarter ASC
        """,
        "backtest_results_lookup": """
            EXPLAIN QUERY PLAN
            SELECT *
            FROM backtest_results
            WHERE run_id = 'BENCHMARK_RUN' AND symbol = 'INFY'
            ORDER BY evaluation_date ASC
        """,
    }

    for qname, qsql in queries.items():
        plan_rows = cursor.execute(qsql).fetchall()
        plan_details = [
            f"id={r[0]}, parent={r[1]}, notused={r[2]}, detail={r[3]}"
            for r in plan_rows
        ]
        query_plans[qname] = plan_details

    conn.close()

    return indexes, query_plans


def run_benchmark() -> Dict[str, Any]:
    """
    Run comprehensive performance and scalability benchmarks across the data layer.
    """
    print("=" * 70)
    print("WEEK 15 - PERFORMANCE & SCALABILITY BENCHMARK")
    print("=" * 70)

    benchmark_results: List[Dict[str, Any]] = []

    # 1. Available Stocks (50 universe)
    res = time_operation(
        "Universe Discovery (get_available_stocks)",
        lambda: get_available_stocks(),
        iterations=5,
    )
    benchmark_results.append(res)
    print(f"[OK] {res['operation']:<48} {res['avg_ms']:>8.2f} ms ({res['row_count']} stocks)")

    # 2. Single-Stock OHLCV (INFY, TCS, RELIANCE)
    for sym in ["INFY", "TCS", "RELIANCE"]:
        res = time_operation(
            f"Single-Stock OHLCV ({sym})",
            lambda s=sym: get_stock_data(s),
            iterations=5,
        )
        benchmark_results.append(res)
        print(f"[OK] {res['operation']:<48} {res['avg_ms']:>8.2f} ms ({res['row_count']} rows)")

    # 3. Latest Price Lookup
    for sym in ["INFY", "HDFCBANK"]:
        res = time_operation(
            f"Latest Price Lookup ({sym})",
            lambda s=sym: get_latest_price(s),
            iterations=10,
        )
        benchmark_results.append(res)
        print(f"[OK] {res['operation']:<48} {res['avg_ms']:>8.2f} ms")

    # 4. Single-Stock 1-Year Historical Range
    res = time_operation(
        "Historical 1-Year Range (INFY, 2025-01-01 -> 2026-01-01)",
        lambda: get_stock_data("INFY", start_date="2025-01-01", end_date="2026-01-01"),
        iterations=5,
    )
    benchmark_results.append(res)
    print(f"[OK] {res['operation']:<48} {res['avg_ms']:>8.2f} ms ({res['row_count']} rows)")

    # 5. Technical Indicator Retrieval
    for sym in ["INFY", "TCS"]:
        res = time_operation(
            f"Technical Indicators Retrieval ({sym})",
            lambda s=sym: get_technical_indicators(s),
            iterations=5,
        )
        benchmark_results.append(res)
        print(f"[OK] {res['operation']:<48} {res['avg_ms']:>8.2f} ms ({res['row_count']} rows)")

    # 6. Financial Data Retrieval (Quarterly Series & Latest Record)
    for sym in ["INFY", "RELIANCE"]:
        res_full = time_operation(
            f"Financial History Retrieval ({sym})",
            lambda s=sym: get_financial_data(s),
            iterations=5,
        )
        benchmark_results.append(res_full)
        print(f"[OK] {res_full['operation']:<48} {res_full['avg_ms']:>8.2f} ms ({res_full['row_count']} quarters)")

        res_latest = time_operation(
            f"Latest Financial Record ({sym})",
            lambda s=sym: get_latest_financial_data(s),
            iterations=5,
        )
        benchmark_results.append(res_latest)
        print(f"[OK] {res_latest['operation']:<48} {res_latest['avg_ms']:>8.2f} ms")

    # 7. Backtest Input Retrieval (get_backtest_inputs)
    for sym in ["INFY", "TCS"]:
        res_bt = time_operation(
            f"Backtest Inputs Retrieval ({sym}, 1-month window)",
            lambda s=sym: get_backtest_inputs(s, "2025-08-01", "2025-08-28"),
            iterations=3,
        )
        benchmark_results.append(res_bt)
        print(f"[OK] {res_bt['operation']:<48} {res_bt['avg_ms']:>8.2f} ms ({res_bt['row_count']} records)")

    # 8. Full 50-Stock Universe Multi-Stock Extraction
    def fetch_full_50_universe_prices():
        stocks = get_available_stocks()["symbol"].tolist()
        total_rows = 0
        for s in stocks:
            df = get_stock_data(s)
            total_rows += len(df)
        return total_rows

    t0 = time.perf_counter()
    full_50_rows = fetch_full_50_universe_prices()
    t1 = time.perf_counter()
    full_50_time_ms = (t1 - t0) * 1000.0

    res_50 = {
        "operation": "50-Stock Universe Full Market Extraction",
        "iterations": 1,
        "avg_ms": round(full_50_time_ms, 2),
        "min_ms": round(full_50_time_ms, 2),
        "max_ms": round(full_50_time_ms, 2),
        "row_count": full_50_rows,
        "peak_memory_kb": 0.0,
    }
    benchmark_results.append(res_50)
    print(f"\n[OK] {res_50['operation']:<48} {res_50['avg_ms']:>8.2f} ms ({res_50['row_count']} total rows)")

    # 9. Backtest Result Persistence & Retrieval Benchmark
    run_id = f"BENCHMARK_RUN_{int(time.time())}"
    sample_results = [
        {
            "run_id": run_id,
            "symbol": "INFY",
            "evaluation_date": f"2025-08-{d:02d}",
            "result_metadata": {
                "opportunity_score": 75.5 + d,
                "recommendation": "BUY" if d % 2 == 0 else "WATCH",
                "status": "VALID",
            },
        }
        for d in range(1, 21)
    ]

    res_store = time_operation(
        "Backtest Result Batch Store (20 records)",
        lambda: store_backtest_results(sample_results),
        iterations=1,
    )
    benchmark_results.append(res_store)
    print(f"[OK] {res_store['operation']:<48} {res_store['avg_ms']:>8.2f} ms ({res_store['row_count']} stored)")

    res_retrieve = time_operation(
        "Backtest Result Filtered Retrieval",
        lambda: get_backtest_results(run_id=run_id, symbol="INFY"),
        iterations=5,
    )
    benchmark_results.append(res_retrieve)
    print(f"[OK] {res_retrieve['operation']:<48} {res_retrieve['avg_ms']:>8.2f} ms ({res_retrieve['row_count']} records)")

    # Clean up benchmark backtest run
    conn = sqlite3.connect(DATABASE_PATH)
    conn.execute("DELETE FROM backtest_results WHERE run_id = ?", (run_id,))
    conn.commit()
    conn.close()

    # Index Review
    indexes, query_plans = review_database_indexes()

    report_payload = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "benchmark_summary": benchmark_results,
        "indexes": indexes,
        "query_plans": query_plans,
    }

    report_file = REPORTS_DIR / "week15_performance_benchmark.json"
    with open(report_file, "w", encoding="utf-8") as f:
        json.dump(report_payload, f, indent=2)

    print("\n" + "=" * 70)
    print(f"BENCHMARK COMPLETED — Report saved to {report_file}")
    print("=" * 70)

    return report_payload


if __name__ == "__main__":
    run_benchmark()
