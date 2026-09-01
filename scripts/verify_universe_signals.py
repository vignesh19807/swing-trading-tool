import time
import pandas as pd
from backend.data_pipeline.data_service import get_available_stocks
from backend.logic.signal_integration import run_signal_pipeline

def main():
    print("======================================================")
    print("WEEK 8 FRIDAY - CURRENT UNIVERSE END-TO-END VERIFICATION")
    print("======================================================")

    start_time = time.time()

    try:
        stocks_df = get_available_stocks()
        symbols = stocks_df['symbol'].tolist()
    except Exception as e:
        print(f"Failed to get available stocks: {e}")
        return

    total_attempted = len(symbols)
    successful_evaluations = 0
    valid_signals = 0
    invalid_signals = 0
    errors = 0

    recommendation_counts = {}
    reason_counts = {}
    valid_examples = []
    missing_data_examples = []

    print(f"Total stocks to evaluate: {total_attempted}")

    for symbol in symbols:
        try:
            signal = run_signal_pipeline(symbol)
            successful_evaluations += 1

            # Recommendation count
            rec = signal.get("recommendation")
            rec_key = rec if rec is not None else "UNKNOWN"
            recommendation_counts[rec_key] = recommendation_counts.get(rec_key, 0) + 1

            # Final Signal State Count
            if signal.get("signal_valid"):
                valid_signals += 1
                valid_examples.append(signal)
            else:
                invalid_signals += 1
                reason = signal.get("reason", "UNKNOWN")
                reason_counts[reason] = reason_counts.get(reason, 0) + 1

                if reason in ["MISSING_OR_INVALID_INPUTS", "INSUFFICIENT_DATA", "NOT_A_BUY_RECOMMENDATION"]:
                    missing_data_examples.append(signal)

        except Exception as e:
            errors += 1
            print(f"Exception for {symbol}: {e}")

    # Historical evaluation date verification
    print("\n--- HISTORICAL EVALUATION DATE VERIFICATION ---")
    try:
        hist_signal = run_signal_pipeline("RELIANCE", evaluation_date="2026-08-14")
        print(f"RELIANCE (2026-08-14) Result:")
        for k, v in hist_signal.items():
            print(f"  {k}: {v}")
    except Exception as e:
        print(f"Historical verification failed: {e}")

    end_time = time.time()

    print("\n======================================================")
    print("FINAL REPORT")
    print("======================================================")
    print(f"A. Universe source          : backend.data_pipeline.data_service.get_available_stocks()")
    print(f"B. Total stocks attempted   : {total_attempted}")
    print(f"C. Successful evaluations   : {successful_evaluations}")
    print(f"D. Valid signals            : {valid_signals}")
    print(f"E. Invalid/rejected signals : {invalid_signals}")
    print(f"F. Errors                   : {errors}")
    print(f"J. Execution time           : {end_time - start_time:.2f} seconds")

    print("\nCount by recommendation (BUY/HOLD/AVOID/etc.):")
    for rec, count in sorted(recommendation_counts.items()):
        print(f"  {rec}: {count}")

    print("\nCount by final signal reason (State):")
    for reason, count in sorted(reason_counts.items()):
        print(f"  {reason}: {count}")

    print("\nG. Valid Signal Examples:")
    if not valid_examples:
        print("  None")
    for ex in valid_examples[:10]:
        print(f"  {ex['symbol']}: Rec={ex.get('recommendation')} | Entry: {ex.get('entry_lower')}-{ex.get('entry_upper')} | Stop: {ex.get('stop_loss')} | Target: {ex.get('target')} | Risk: {ex.get('risk')} | Reward: {ex.get('reward')} | R:R: {ex.get('risk_reward_ratio')} | Reason: {ex.get('reason')}")

    print("\nH. Missing-data / Rejected Examples:")
    if not missing_data_examples:
        print("  None")
    for ex in missing_data_examples[:10]:
        print(f"  {ex['symbol']}: Reason={ex.get('reason')} | Missing: {ex.get('missing_inputs')}")

if __name__ == "__main__":
    main()
