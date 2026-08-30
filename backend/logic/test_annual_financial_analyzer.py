"""
Tests for Annual Financial Analyzer v1 (Including Tuesday CAGR)
"""

import pytest
from backend.logic.annual_financial_analyzer import analyze_annual_financials, calculate_cagr

def test_calculate_cagr_unit():
    """Unit test for the pure CAGR calculation logic."""
    # Basic 3 years
    assert calculate_cagr(100.0, 133.1, 3.0) == pytest.approx(10.0, rel=1e-2)
    # Zero years
    assert calculate_cagr(100.0, 110.0, 0.0) is None
    # Zero or negative start
    assert calculate_cagr(0.0, 100.0, 2.0) is None
    assert calculate_cagr(-50.0, 100.0, 2.0) is None
    # Missing data
    assert calculate_cagr(None, 100.0, 2.0) is None
    assert calculate_cagr(100.0, None, 2.0) is None


def test_analyze_annual_financials_valid_with_cagr():
    """Test with complete, chronologically sorted annual records and valid CAGR."""
    records = [
        {
            "symbol": "INFY",
            "period": "2021-03-31",
            "revenue": 1000.0,
            "net_profit": 100.0,
            "eps": 10.0,
            "roe": 0.15,
            "roce": 0.20
        },
        {
            "symbol": "INFY",
            "period": "2024-03-31", # Approx 3 years later
            "revenue": 1331.0, # 10% CAGR over 3 years
            "net_profit": 172.8, # 20% CAGR over 3 years
            "eps": 17.28,
            "roe": 0.16,
            "roce": 0.22
        }
    ]

    res = analyze_annual_financials(records)

    assert res["symbol"] == "INFY"
    assert res["status"] == "VALID"
    assert res["latest_period"] == "2024-03-31"

    assert res["revenue_cagr"] == pytest.approx(10.0, rel=1e-2)
    assert res["net_profit_cagr"] == pytest.approx(20.0, rel=1e-2)


def test_cagr_with_missing_start_or_end():
    """Test CAGR skipping None values at the start or end."""
    records = [
        {
            "symbol": "TCS",
            "period": "2022-03-31",
            "revenue": None, # Missing start revenue
            "net_profit": 200.0,
            "eps": 10.0, "roe": 0.1, "roce": 0.1
        },
        {
            "symbol": "TCS",
            "period": "2023-03-31",
            "revenue": 1100.0, # First valid revenue
            "net_profit": None, # Missing mid profit
            "eps": 10.0, "roe": 0.1, "roce": 0.1
        },
        {
            "symbol": "TCS",
            "period": "2024-03-31",
            "revenue": 1210.0,
            "net_profit": 242.0,
            "eps": 10.0, "roe": 0.1, "roce": 0.1
        }
    ]

    res = analyze_annual_financials(records)
    # Revenue start is 2023 (1100), end is 2024 (1210) -> 1 year -> 10%
    assert res["revenue_cagr"] == pytest.approx(10.0, rel=1e-2)

    # Profit start is 2022 (200), end is 2024 (242) -> 2 years -> 10%
    assert res["net_profit_cagr"] == pytest.approx(10.0, rel=1e-2)


def test_cagr_with_negative_start_value():
    """Test CAGR returns None for negative starting profit."""
    records = [
        {
            "symbol": "RELIANCE",
            "period": "2023-03-31",
            "revenue": 1000.0,
            "net_profit": -50.0, # Negative!
            "eps": 10.0, "roe": 0.1, "roce": 0.1
        },
        {
            "symbol": "RELIANCE",
            "period": "2024-03-31",
            "revenue": 1100.0,
            "net_profit": 50.0,
            "eps": 10.0, "roe": 0.1, "roce": 0.1
        }
    ]

    res = analyze_annual_financials(records)
    assert res["revenue_cagr"] == pytest.approx(10.0, rel=1e-2)
    assert res["net_profit_cagr"] is None # Handled safely


def test_analyze_annual_financials_chronology():
    """Test that analyzer correctly sorts records chronologically."""
    records = [
        {
            "symbol": "TCS",
            "period": "2025-03-31", # Later date
            "revenue": 2200.0,
            "net_profit": 350.0,
            "eps": 18.0,
            "roe": 0.22,
            "roce": 0.28
        },
        {
            "symbol": "TCS",
            "period": "2024-03-31", # Earlier date
            "revenue": 2000.0,
            "net_profit": 400.0, # Net profit was higher before
            "eps": 20.0,
            "roe": 0.25,
            "roce": 0.30
        }
    ]

    res = analyze_annual_financials(records)

    assert res["status"] == "VALID"
    assert res["latest_period"] == "2025-03-31"

    assert res["latest_revenue"] == 2200.0
    assert res["revenue_yoy_growth"] == 10.0
    assert res["revenue_trend"] == "Improving"
    assert res["revenue_cagr"] == pytest.approx(10.0, rel=1e-2)

    assert res["latest_net_profit"] == 350.0
    assert res["net_profit_yoy_growth"] == -12.5
    assert res["net_profit_trend"] == "Declining"
    assert res["net_profit_cagr"] == pytest.approx(-12.5, rel=1e-2)


def test_analyze_annual_financials_missing_eps():
    """Test that missing EPS does not fail analysis."""
    records = [
        {
            "symbol": "WIPRO",
            "period": "2023-03-31",
            "revenue": 500.0,
            "net_profit": 50.0,
            "eps": None,
            "roe": 0.10,
            "roce": 0.15
        },
        {
            "symbol": "WIPRO",
            "period": "2024-03-31",
            "revenue": 510.0,
            "net_profit": 51.0,
            "eps": None,
            "roe": 0.10,
            "roce": 0.15
        }
    ]

    res = analyze_annual_financials(records)

    assert res["status"] == "VALID"
    assert res["latest_revenue"] == 510.0
    assert res["latest_eps"] is None
    assert res["eps_yoy_growth"] is None
    assert res["eps_trend"] == "Insufficient Data"


def test_analyze_annual_financials_insufficient_data():
    """Test with 0 or 1 record."""
    records = [
        {
            "symbol": "RELIANCE",
            "period": "2024-03-31",
            "revenue": 5000.0,
            "net_profit": 500.0,
            "eps": 50.0,
            "roe": 0.15,
            "roce": 0.20
        }
    ]

    res = analyze_annual_financials(records)
    assert res["status"] == "PARTIAL" # 1 record is PARTIAL, <2 cannot calculate growth
    assert res["revenue_yoy_growth"] is None
    assert res["revenue_cagr"] is None
    assert res["revenue_trend"] == "Insufficient Data"

    res_empty = analyze_annual_financials([])
    assert res_empty["status"] == "INSUFFICIENT"


def test_analyze_annual_financials_invalid_period():
    """Test with malformed/invalid periods."""
    records = [
        {
            "symbol": "HDFCBANK",
            "period": "INVALID-DATE",
            "revenue": 500.0,
            "net_profit": 50.0,
            "eps": 10.0,
            "roe": 0.1,
            "roce": 0.1
        },
        {
            "symbol": "HDFCBANK",
            "period": "ALSO-INVALID",
            "revenue": 510.0,
            "net_profit": 55.0,
            "eps": 11.0,
            "roe": 0.1,
            "roce": 0.1
        }
    ]

    res = analyze_annual_financials(records)
    assert res["status"] == "INSUFFICIENT"


def test_analyze_annual_financials_no_conversion_to_zero():
    """Ensure None values are not converted to 0.0 during growth logic."""
    records = [
        {
            "symbol": "TEST",
            "period": "2023-03-31",
            "revenue": 100.0,
            "net_profit": None,
            "eps": None,
            "roe": None,
            "roce": None
        },
        {
            "symbol": "TEST",
            "period": "2024-03-31",
            "revenue": 110.0,
            "net_profit": None,
            "eps": None,
            "roe": None,
            "roce": None
        }
    ]

    res = analyze_annual_financials(records)
    assert res["status"] == "PARTIAL" # Revenue exists, net profit missing

    assert res["latest_revenue"] == 110.0
    assert res["revenue_trend"] == "Improving"
    assert res["revenue_cagr"] == pytest.approx(10.0, rel=1e-2)

    assert res["latest_net_profit"] is None
    assert res["net_profit_trend"] == "Insufficient Data"
    assert res["net_profit_cagr"] is None
    assert res["latest_eps"] is None
    assert res["latest_roe"] is None
    assert res["latest_roce"] is None
