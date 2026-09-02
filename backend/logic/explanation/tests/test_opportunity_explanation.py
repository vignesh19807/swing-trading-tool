import pytest
import pandas as pd
from backend.logic.explanation.opportunity_explanation import explain_opportunity

def test_explain_opportunity_insufficient():
    decision_payload = {
        "symbol": "TCS",
        "status": "INSUFFICIENT",
        "opportunity_score": None,
        "recommendation": "INSUFFICIENT_DATA"
    }
    res = explain_opportunity(decision_payload, None, None, "2024-05-20")

    assert res["symbol"] == "TCS"
    assert res["opportunity_score"] is None
    assert res["status"] == "INSUFFICIENT"
    assert "aborted due to missing mandatory data" in res["explanation"]["summary"]
    assert len(res["explanation"]["missing_factors"]) == 1

def test_explain_opportunity_full_data():
    decision_payload = {
        "symbol": "TCS",
        "status": "VALID",
        "opportunity_score": 75.5,
        "recommendation": "BUY",
        "technical_score": 80.0,
        "financial_score": 70.0,
        "momentum_score": 85.0,
        "sector_intelligence": {
            "stock_sector": "IT",
            "sector_rankings": [{
                "sector": "IT",
                "rank": 1,
                "performance": 0.05
            }]
        }
    }
    indicators_df = pd.DataFrame([{
        "rsi": 55.0, "rsi_score": 25.0, "macd": 1.5, "signal": 1.0,
        "macd_score": 25.0, "close": 150.0, "ema50": 130.0, "trend_score": 15.0,
        "volume_score": 15.0
    }])
    financial_result = {
        "profitability_score": 90.0,
        "growth_score": 85.0,
        "valuation_score": 95.0,
        "component_statuses": {"roe": "VALID", "growth": "VALID", "valuation": "VALID"}
    }

    res = explain_opportunity(decision_payload, indicators_df, financial_result, "2024-05-20")

    assert res["opportunity_score"] == 75.5
    assert res["score_breakdown"]["technical_weight"] == 0.40
    assert res["score_breakdown"]["technical_weighted_contribution"] == 32.0
    assert res["score_breakdown"]["financial_weight"] == 0.35
    assert res["score_breakdown"]["financial_weighted_contribution"] == 24.5
    assert res["score_breakdown"]["momentum_weight"] == 0.25
    assert res["score_breakdown"]["momentum_weighted_contribution"] == 21.25

    # Check factors classification
    assert len(res["explanation"]["positive_factors"]) == 8 # 4 tech, 3 fin, 1 mom
    assert len(res["explanation"]["missing_factors"]) == 0
    assert "BUY recommendation driven by strong contributing factors" in res["explanation"]["summary"]
    assert "IT sector is currently ranked #1" in res["explanation"]["sector_context"]

def test_explain_opportunity_missing_momentum():
    decision_payload = {
        "symbol": "HDFC",
        "status": "PARTIAL",
        "opportunity_score": 70.0,
        "recommendation": "WATCH",
        "technical_score": 60.0,
        "financial_score": 80.0,
        "momentum_score": None
    }
    # dynamic weights: tech = 0.40/0.75 = 0.5333, fin = 0.35/0.75 = 0.4667
    expected_tech_contrib = 60.0 * (0.40 / 0.75)
    expected_fin_contrib = 80.0 * (0.35 / 0.75)

    res = explain_opportunity(decision_payload, None, None, "2024-05-20")

    assert res["score_breakdown"]["momentum_score"] is None
    assert round(res["score_breakdown"]["technical_weight"], 4) == round(0.40/0.75, 4)
    assert round(res["score_breakdown"]["technical_weighted_contribution"], 4) == round(expected_tech_contrib, 4)
    assert round(res["score_breakdown"]["financial_weight"], 4) == round(0.35/0.75, 4)
    assert round(res["score_breakdown"]["financial_weighted_contribution"], 4) == round(expected_fin_contrib, 4)

    # Missing momentum should be in missing factors
    missing = res["explanation"]["missing_factors"]
    assert len(missing) == 1
    assert missing[0]["category"] == "Momentum"

    # Summary should note missing momentum
    assert "dynamically overweighted" in res["explanation"]["summary"]

def test_explain_opportunity_hold():
    decision_payload = {
        "symbol": "INFY",
        "status": "VALID",
        "opportunity_score": 50.0,
        "recommendation": "HOLD",
        "technical_score": 45.0,
        "financial_score": 55.0,
        "momentum_score": 50.0,
        "sector_intelligence": None
    }
    res = explain_opportunity(decision_payload, None, None, "2024-05-20")
    assert res["opportunity_score"] == 50.0
    assert "generates a HOLD recommendation" in res["explanation"]["summary"]
    assert "moderate or mixed signals" in res["explanation"]["summary"]

def test_explain_opportunity_avoid():
    decision_payload = {
        "symbol": "WIPRO",
        "status": "VALID",
        "opportunity_score": 30.0,
        "recommendation": "AVOID",
        "technical_score": 30.0,
        "financial_score": 30.0,
        "momentum_score": 30.0,
        "sector_intelligence": None
    }
    res = explain_opportunity(decision_payload, None, None, "2024-05-20")
    assert res["opportunity_score"] == 30.0
    assert "generates an AVOID recommendation" in res["explanation"]["summary"]
    assert "weak technical or financial metrics" in res["explanation"]["summary"]
