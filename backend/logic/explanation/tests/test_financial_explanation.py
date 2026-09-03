import pytest

from backend.logic.explanation.financial_explanation import (
    explain_profitability,
    explain_growth,
    explain_valuation,
    explain_financial_factors
)

def test_explain_profitability_positive():
    fin_result = {
        "profitability_score": 90.0,
        "component_statuses": {"roe": "VALID"}
    }
    res = explain_profitability(fin_result)
    assert res["sentiment"] == "positive"
    assert res["metric"] == "Profitability"

def test_explain_profitability_negative():
    fin_result = {
        "profitability_score": 30.0,
        "component_statuses": {"roe": "VALID"}
    }
    res = explain_profitability(fin_result)
    assert res["sentiment"] == "negative"

def test_explain_profitability_neutral():
    fin_result = {
        "profitability_score": 60.0,
        "component_statuses": {"roe": "VALID"}
    }
    res = explain_profitability(fin_result)
    assert res["sentiment"] == "neutral"

def test_explain_profitability_missing():
    fin_result = {
        "profitability_score": None,
        "component_statuses": {"roe": "INSUFFICIENT", "roce": "INSUFFICIENT", "profit_margin": "INSUFFICIENT"}
    }
    res = explain_profitability(fin_result)
    assert res["sentiment"] == "missing"
    assert res["value"] == "Unavailable upstream"

def test_explain_growth_positive():
    fin_result = {
        "growth_score": 95.0,
        "component_statuses": {"growth": "VALID"}
    }
    res = explain_growth(fin_result)
    assert res["sentiment"] == "positive"

def test_explain_growth_negative():
    fin_result = {
        "growth_score": 40.0,
        "component_statuses": {"growth": "VALID"}
    }
    res = explain_growth(fin_result)
    assert res["sentiment"] == "negative"

def test_explain_valuation_positive():
    fin_result = {
        "valuation_score": 100.0,
        "component_statuses": {"valuation": "VALID"}
    }
    res = explain_valuation(fin_result)
    assert res["sentiment"] == "positive"

def test_explain_valuation_negative():
    fin_result = {
        "valuation_score": 20.0,
        "component_statuses": {"valuation": "VALID"}
    }
    res = explain_valuation(fin_result)
    assert res["sentiment"] == "negative"

def test_explain_financial_factors():
    fin_result = {
        "profitability_score": 90.0,
        "growth_score": 85.0,
        "valuation_score": 95.0,
        "component_statuses": {
            "roe": "VALID",
            "growth": "VALID",
            "valuation": "VALID"
        }
    }
    factors = explain_financial_factors(fin_result)
    assert len(factors) == 3
    for f in factors:
        assert f["sentiment"] == "positive"
