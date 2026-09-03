import pytest
from backend.logic.explanation.sector_explanation import explain_sector_context

def test_explain_sector_context_unavailable_payload():
    res = explain_sector_context("TCS", None)
    assert res == "Sector intelligence is currently unavailable."

def test_explain_sector_context_missing_stock_sector():
    sector_intel = {"sector_rankings": []}
    res = explain_sector_context("TCS", sector_intel)
    assert "Sector classification for 'TCS' is unavailable" in res

def test_explain_sector_context_empty_rankings():
    sector_intel = {"stock_sector": "IT", "sector_rankings": []}
    res = explain_sector_context("TCS", sector_intel)
    assert "Sector rankings are empty" in res

def test_explain_sector_context_sector_not_found():
    sector_intel = {
        "stock_sector": "IT",
        "sector_rankings": [{"sector": "Finance"}]
    }
    res = explain_sector_context("TCS", sector_intel)
    assert "was not found in the current sector intelligence rankings" in res

def test_explain_sector_context_insufficient_data():
    sector_intel = {
        "stock_sector": "IT",
        "sector_rankings": [{
            "sector": "IT",
            "rank": None,
            "performance": None,
            "data_quality": "INSUFFICIENT_DATA"
        }]
    }
    res = explain_sector_context("TCS", sector_intel)
    assert "could not be fully analyzed" in res
    assert "INSUFFICIENT_DATA" in res

def test_explain_sector_context_valid_full_data():
    sector_intel = {
        "ranking_period": "63D",
        "stock_sector": "IT",
        "sector_rankings": [{
            "sector": "IT",
            "rank": 2,
            "performance": 0.052,
            "data_quality": "VALID",
            "relative_strength": {
                "status": "VALID",
                "benchmark": "NIFTY_50",
                "63D_rs": 0.021
            }
        }]
    }
    res = explain_sector_context("TCS", sector_intel)
    assert "IT sector is currently ranked #2" in res
    assert "63D absolute return of +5.2%" in res
    assert "outperforming the NIFTY_50 benchmark by 2.1%" in res

def test_explain_sector_context_unavailable_benchmark():
    sector_intel = {
        "ranking_period": "21D",
        "stock_sector": "Finance",
        "sector_rankings": [{
            "sector": "Finance",
            "rank": 5,
            "performance": -0.015,
            "data_quality": "VALID",
            "relative_strength": {
                "status": "UNAVAILABLE"
            }
        }]
    }
    res = explain_sector_context("HDFC", sector_intel)
    assert "Finance sector is currently ranked #5" in res
    assert "21D absolute return of -1.5%" in res
    assert "benchmark relative strength is unavailable" in res

def test_explain_sector_context_partial_benchmark():
    sector_intel = {
        "ranking_period": "126D",
        "stock_sector": "Auto",
        "sector_rankings": [{
            "sector": "Auto",
            "rank": 1,
            "performance": 0.10,
            "data_quality": "VALID",
            "relative_strength": {
                "status": "PARTIAL",
                "benchmark": "NIFTY_50"
                # 126D_rs is missing
            }
        }]
    }
    res = explain_sector_context("MARUTI", sector_intel)
    assert "Auto sector is currently ranked #1" in res
    assert "126D absolute return of +10.0%" in res
    assert "relative strength vs NIFTY_50 is partially missing" in res
