"""
Tests for Red Flag Analyzer v1 (Wednesday)
"""

import pytest
from backend.logic.red_flag_analyzer import detect_red_flags

def test_no_red_flags_healthy_data():
    """A. No red flags for healthy/stable data."""
    # This simulates output from annual_financial_analyzer
    healthy_analysis = {
        "status": "VALID",
        "revenue_trend": "Improving",
        "revenue_cagr": 15.0,
        "net_profit_trend": "Improving",
        "net_profit_cagr": 20.0,
        "roe_trend": "Stable",
        "roce_trend": "Improving",
        "eps_trend": "Improving"
    }

    res = detect_red_flags(healthy_analysis)
    assert res["has_red_flags"] is False
    assert len(res["red_flags"]) == 0


def test_revenue_and_profit_deterioration():
    """B, C, F. Revenue and Net Profit deterioration, multiple flags."""
    deteriorating_analysis = {
        "status": "VALID",
        "revenue_trend": "Declining",
        "revenue_cagr": -2.0,
        "net_profit_trend": "Declining",
        "net_profit_cagr": -5.0,
        "roe_trend": "Stable",
        "roce_trend": "Stable"
    }

    res = detect_red_flags(deteriorating_analysis)
    assert res["has_red_flags"] is True
    assert len(res["red_flags"]) == 2

    types = [f["type"] for f in res["red_flags"]]
    assert "revenue_decline" in types
    assert "net_profit_decline" in types

    # Check reason is present
    for flag in res["red_flags"]:
        assert "reason" in flag
        assert len(flag["reason"]) > 10


def test_roe_and_roce_deterioration():
    """D, E. ROE and ROCE deterioration."""
    deteriorating_efficiency = {
        "status": "VALID",
        "revenue_trend": "Improving",
        "net_profit_trend": "Stable",
        "roe_trend": "Declining",
        "roce_trend": "Declining"
    }

    res = detect_red_flags(deteriorating_efficiency)
    assert res["has_red_flags"] is True
    assert len(res["red_flags"]) == 2

    types = [f["type"] for f in res["red_flags"]]
    assert "roe_decline" in types
    assert "roce_decline" in types


def test_missing_data_safety():
    """G, H, I, J, K, P, Q. Missing data does not create false positives."""
    missing_analysis = {
        "status": "PARTIAL",
        "revenue_trend": "Insufficient Data",
        "revenue_cagr": None,
        "net_profit_trend": "Insufficient Data",
        "net_profit_cagr": None,
        "roe_trend": "Insufficient Data",
        "roce_trend": "Insufficient Data",
        "eps_trend": "Insufficient Data"
    }

    res = detect_red_flags(missing_analysis)
    assert res["has_red_flags"] is False
    assert len(res["red_flags"]) == 0


def test_insufficient_history():
    """L. Insufficient annual history."""
    insufficient = {
        "status": "INSUFFICIENT"
    }

    res = detect_red_flags(insufficient)
    assert res["has_red_flags"] is False
    assert len(res["red_flags"]) == 0


def test_structured_output_keys():
    """O. Structured output keys and types."""
    analysis = {
        "status": "VALID",
        "revenue_trend": "Declining"
    }

    res = detect_red_flags(analysis)
    assert isinstance(res["has_red_flags"], bool)
    assert isinstance(res["red_flags"], list)

    flag = res["red_flags"][0]
    assert "type" in flag
    assert "severity" in flag
    assert "metric" in flag
    assert "reason" in flag
    assert isinstance(flag["type"], str)
    assert isinstance(flag["reason"], str)


def test_five_stocks_simulation():
    """Simulating the 5 standard stock fixtures."""
    # 1. INFY - Healthy
    assert detect_red_flags({
        "status": "VALID", "revenue_trend": "Improving", "net_profit_trend": "Improving", "roe_trend": "Improving", "roce_trend": "Improving"
    })["has_red_flags"] is False

    # 2. TCS - Stable
    assert detect_red_flags({
        "status": "VALID", "revenue_trend": "Stable", "net_profit_trend": "Stable", "roe_trend": "Stable", "roce_trend": "Stable"
    })["has_red_flags"] is False

    # 3. WIPRO - Declining profit
    res_wipro = detect_red_flags({
        "status": "VALID", "revenue_trend": "Stable", "net_profit_trend": "Declining", "roe_trend": "Stable", "roce_trend": "Declining"
    })
    assert res_wipro["has_red_flags"] is True
    assert len(res_wipro["red_flags"]) == 2

    # 4. RELIANCE - Missing ROE
    assert detect_red_flags({
        "status": "VALID", "revenue_trend": "Improving", "net_profit_trend": "Improving", "roe_trend": "Insufficient Data", "roce_trend": "Insufficient Data"
    })["has_red_flags"] is False

    # 5. HDFCBANK - Complete disaster
    res_hdfc = detect_red_flags({
        "status": "VALID", "revenue_trend": "Declining", "net_profit_trend": "Declining", "roe_trend": "Declining", "roce_trend": "Declining"
    })
    assert res_hdfc["has_red_flags"] is True
    assert len(res_hdfc["red_flags"]) == 4
