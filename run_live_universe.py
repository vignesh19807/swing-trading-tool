"""
Live Universe Script
====================
Runs the End-to-End ranking universe over the actual local SQLite database.
DO NOT IMPORT INTO PRODUCTION APPS. This is a manual test/execution script.
"""

import json
from pprint import pprint
import time

from backend.engines.universe_orchestrator import rank_universe

def run_live():
    print("==========================================")
    print("SWING TRADING PLATFORM - UNIVERSE RANKER")
    print("==========================================")

    start_time = time.time()

    # Run the orchestrator
    print("\nFetching universe and ranking stocks...")
    result = rank_universe()

    elapsed = time.time() - start_time

    print("\n==========================================")
    print("TOP 10 RESULT")
    print("==========================================")
    for i, stock in enumerate(result["top_10"], 1):
        print(f"[{i}] {stock['symbol']} | Final: {stock['final_ranking_score']} "
              f"| Opp: {stock.get('opportunity_score')} | Sector: {stock.get('sector_score')} "
              f"| Rec: {stock.get('recommendation')}")

    print("\n==========================================")
    print("UNRANKED RESULT SUMMARY")
    print("==========================================")
    unranked = result["unranked"]
    missing_core = [s for s in unranked if s["reason"] == "MISSING_CORE_OPPORTUNITY_SCORE"]
    outside_top = [s for s in unranked if s["reason"] == "OUTSIDE_TOP_10"]

    print(f"Total Unranked: {len(unranked)}")
    print(f" - Outside Top 10: {len(outside_top)}")
    print(f" - Missing Core/Insufficient: {len(missing_core)}")
    if missing_core:
        print("   -> " + ", ".join([s['symbol'] for s in missing_core[:10]]) + ("..." if len(missing_core) > 10 else ""))

    print("\n==========================================")
    print(f"Execution Time: {elapsed:.2f} seconds")
    print(f"Total Attempted: {len(result['top_10']) + len(unranked)}")
    print("==========================================\n")

if __name__ == "__main__":
    run_live()
