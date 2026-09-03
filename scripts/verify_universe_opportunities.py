import time
from backend.engines.universe_orchestrator import rank_universe

def main():
    print("======================================================")
    print("WEEK 9 FRIDAY - TOP 10 OPPORTUNITY EXPLANATIONS")
    print("======================================================")

    start_time = time.time()

    print("Running full universe ranking & explanation...")
    try:
        ranking_result = rank_universe()
    except Exception as e:
        print(f"Failed to run universe orchestrator: {e}")
        return

    top_10 = ranking_result.get("top_10", [])

    print(f"\nTop 10 Opportunities Generated in {time.time() - start_time:.2f} seconds\n")

    for stock in top_10:
        rank = stock.get("rank")
        symbol = stock.get("symbol")
        opp_score = stock.get("opportunity_score")
        rec = stock.get("recommendation")

        explanation = stock.get("structured_explanation", {})
        summary = explanation.get("explanation", {}).get("summary", "No summary available")
        pos_factors = len(explanation.get("explanation", {}).get("positive_factors", []))
        neg_factors = len(explanation.get("explanation", {}).get("negative_factors", []))
        missing_factors = len(explanation.get("explanation", {}).get("missing_factors", []))
        sector_context = explanation.get("explanation", {}).get("sector_context", "No sector context")

        print(f"[{rank}] {symbol} | Score: {opp_score} | Rec: {rec}")
        print(f"    Summary: {summary}")
        print(f"    Factors: {pos_factors} Positive | {neg_factors} Negative | {missing_factors} Missing")
        print(f"    Sector Context: {sector_context}")
        print("-" * 60)

if __name__ == "__main__":
    main()
