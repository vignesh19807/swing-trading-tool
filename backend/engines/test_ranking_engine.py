"""
Tests for Ranking Engine (Engine 8)
===================================
Verifies Top 10 sorting, fallback rules, truncation, and structural correctness.
"""

import pytest
from backend.engines.ranking_engine import generate_top_10_ranking

def test_valid_multi_stock_ranking():
    """Verify score combination and sort order (DESC final score)."""
    input_data = [
        {
            "symbol": "STOCK_A",
            "status": "VALID",
            "opportunity_score": 80.0,  # 80*0.7 + 90*0.3 = 56 + 27 = 83.0
            "sector_intelligence": {
                "sector_performance": {"preliminary_score": {"score": 90.0}}
            }
        },
        {
            "symbol": "STOCK_B",
            "status": "VALID",
            "opportunity_score": 85.0,  # 85*0.7 + 70*0.3 = 59.5 + 21 = 80.5
            "sector_intelligence": {
                "sector_performance": {"preliminary_score": {"score": 70.0}}
            }
        }
    ]

    res = generate_top_10_ranking(input_data, "2026-08-14")
    top_10 = res["top_10"]

    assert res["evaluation_date"] == "2026-08-14"
    assert len(top_10) == 2
    assert len(res["unranked"]) == 0

    assert top_10[0]["symbol"] == "STOCK_A"
    assert top_10[0]["final_ranking_score"] == 83.0
    assert top_10[0]["rank"] == 1

    assert top_10[1]["symbol"] == "STOCK_B"
    assert top_10[1]["final_ranking_score"] == 80.5
    assert top_10[1]["rank"] == 2

def test_missing_sector_fallback():
    """Verify missing sector score safely defaults to the opportunity score."""
    input_data = [
        {
            "symbol": "STOCK_A",
            "status": "VALID",
            "opportunity_score": 80.0,
            "sector_intelligence": None  # Missing entirely
        },
        {
            "symbol": "STOCK_B",
            "status": "VALID",
            "opportunity_score": 85.0,
            "sector_intelligence": {
                "sector_performance": {"preliminary_score": {"score": None}}
            }
        }
    ]

    res = generate_top_10_ranking(input_data)
    top_10 = res["top_10"]

    assert len(top_10) == 2

    # B is 85.0, A is 80.0. Since both lack sector scores, B > A.
    assert top_10[0]["symbol"] == "STOCK_B"
    assert top_10[0]["final_ranking_score"] == 85.0  # (85*0.7 + 85*0.3)

    assert top_10[1]["symbol"] == "STOCK_A"
    assert top_10[1]["final_ranking_score"] == 80.0  # (80*0.7 + 80*0.3)

def test_deterministic_tie_breaking():
    """Verify identical final scores are broken by opportunity_score, then alphabetically."""
    input_data = [
        {
            "symbol": "ZETA",
            "status": "VALID",
            "opportunity_score": 80.0,
            "sector_intelligence": {"sector_performance": {"preliminary_score": {"score": 80.0}}}
        }, # final 80.0, opp 80.0
        {
            "symbol": "ALPHA",
            "status": "VALID",
            "opportunity_score": 80.0,
            "sector_intelligence": {"sector_performance": {"preliminary_score": {"score": 80.0}}}
        }, # final 80.0, opp 80.0 -> Alpha wins alphabetical tie
        {
            "symbol": "BETA",
            "status": "VALID",
            "opportunity_score": 85.0,
            "sector_intelligence": {"sector_performance": {"preliminary_score": {"score": 68.333333333}}}
        } # final 80.0, opp 85.0 -> Beta wins purely on higher opp score
    ]

    res = generate_top_10_ranking(input_data)
    top_10 = res["top_10"]

    # Beta should be first due to higher opp score
    assert top_10[0]["symbol"] == "BETA"
    # Alpha should be second (alphabetical over Zeta)
    assert top_10[1]["symbol"] == "ALPHA"
    # Zeta should be third
    assert top_10[2]["symbol"] == "ZETA"

def test_top_10_truncation():
    """Verify that > 10 items results in exactly 10 in top_10 and remainder in unranked."""
    input_data = []
    for i in range(15):
        input_data.append({
            "symbol": f"STOCK_{i}",
            "status": "VALID",
            "opportunity_score": float(50 + i), # 50 to 64
            "sector_intelligence": None
        })

    res = generate_top_10_ranking(input_data)
    assert len(res["top_10"]) == 10
    assert len(res["unranked"]) == 5

    # Highest score is STOCK_14
    assert res["top_10"][0]["symbol"] == "STOCK_14"
    assert res["top_10"][9]["symbol"] == "STOCK_5"

    assert res["unranked"][0]["symbol"] == "STOCK_4"
    assert res["unranked"][0]["status"] == "VALID"
    assert res["unranked"][0]["reason"] == "OUTSIDE_TOP_10"

def test_invalid_stocks_segregation():
    """Verify INSUFFICIENT or missing core scores are skipped directly into unranked."""
    input_data = [
        {
            "symbol": "VALID_STOCK",
            "status": "VALID",
            "opportunity_score": 90.0,
            "sector_intelligence": None
        },
        {
            "symbol": "INVALID_STOCK_1",
            "status": "INSUFFICIENT",
            "opportunity_score": None,
            "sector_intelligence": None
        },
        {
            "symbol": "INVALID_STOCK_2",
            "status": "VALID", # Shouldn't happen in practice, but tests robustness
            "opportunity_score": None,
            "sector_intelligence": None
        }
    ]

    res = generate_top_10_ranking(input_data)
    assert len(res["top_10"]) == 1
    assert len(res["unranked"]) == 2

    assert res["top_10"][0]["symbol"] == "VALID_STOCK"

    # Verify reasons
    for unranked in res["unranked"]:
        assert unranked["reason"] == "MISSING_CORE_OPPORTUNITY_SCORE"
