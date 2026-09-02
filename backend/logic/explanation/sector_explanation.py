"""
Sector Explanation Logic
========================

Extracts qualitative contextual information about a stock's sector
based on the existing Sector Intelligence payload.
"""

from typing import Dict, Any, Optional


def explain_sector_context(
    symbol: str,
    sector_intelligence: Optional[Dict[str, Any]]
) -> str:
    """
    Given a symbol and the sector intelligence payload, extracts the sector's
    rank, absolute performance, and relative strength to generate a qualitative string.
    """
    if not sector_intelligence or not isinstance(sector_intelligence, dict):
        return "Sector intelligence is currently unavailable."

    # In accordance with strict requirements, we do NOT query the database.
    # We attempt to find the sector mapping in the sector_intelligence payload itself,
    # or if the decision_payload had injected it (though standard is just symbol).
    # Since the current engine outputs do not embed the specific stock's sector string
    # directly into the decision_payload, and sector_rankings drops constituent lists,
    # it may be genuinely unavailable unless explicitly added upstream in the future.
    sector_name = sector_intelligence.get("stock_sector")
    if not sector_name:
        return f"Sector classification for '{symbol}' is unavailable in the supplied payload."

    sector_rankings = sector_intelligence.get("sector_rankings", [])
    if not sector_rankings:
        return f"Sector rankings are empty. Context for '{sector_name}' is unavailable."

    # Locate the sector within the rankings
    target_sector = None
    for s_data in sector_rankings:
        if s_data.get("sector") == sector_name:
            target_sector = s_data
            break

    if not target_sector:
        return f"Sector '{sector_name}' was not found in the current sector intelligence rankings."

    # Extract metrics
    rank = target_sector.get("rank")
    perf = target_sector.get("performance")
    data_quality = target_sector.get("data_quality", "VALID")

    ranking_period = sector_intelligence.get("ranking_period", "63D")

    if data_quality in ["INSUFFICIENT_DATA", "PARTIAL"] and rank is None:
        return f"Sector '{sector_name}' could not be fully analyzed (data quality: {data_quality}). Ranking and performance are unavailable."

    # Build the string
    context_parts = []

    if rank is not None:
        context_parts.append(f"The {sector_name} sector is currently ranked #{rank}")
    else:
        context_parts.append(f"The {sector_name} sector is currently unranked")

    if perf is not None:
        perf_pct = perf * 100.0
        sign = "+" if perf_pct > 0 else ""
        context_parts.append(f"with a {ranking_period} absolute return of {sign}{perf_pct:.1f}%")

    rs_data = target_sector.get("relative_strength", {})
    rs_status = rs_data.get("status", "UNAVAILABLE")

    if rs_status == "UNAVAILABLE":
        context_parts.append("(benchmark relative strength is unavailable)")
    else:
        benchmark = rs_data.get("benchmark", "Unknown Benchmark")
        rs_key = f"{ranking_period}_rs"
        rs_val = rs_data.get(rs_key)
        if rs_val is not None:
            rs_pct = rs_val * 100.0
            rs_sign = "outperforming" if rs_pct > 0 else "underperforming"
            abs_rs = abs(rs_pct)
            context_parts.append(f"and is {rs_sign} the {benchmark} benchmark by {abs_rs:.1f}% over the same period")
        else:
            context_parts.append(f"(relative strength vs {benchmark} is partially missing)")

    return ", ".join(context_parts) + "."
