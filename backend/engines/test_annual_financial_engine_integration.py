"""
Integration Tests for Financial Engine + Annual Financials (Thursday)
"""

import pytest
from backend.engines.financial_engine import analyze_financial_health

# A deterministic quarterly stub is not strictly needed because we only care about the engine output structure,
# but the financial engine does try to import `backend.logic.*` analyzers.
# So we can just test with existing mockable stock tickers or let the existing real logic run with whatever mock data is normally there.
# If they fail, they return INSUFFICIENT quarterly but the ANNUAL integration should still proceed properly.

@pytest.fixture
def mock_annual_records_infy():
    return [
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
            "period": "2024-03-31",
            "revenue": 1331.0,
            "net_profit": 172.8,
            "eps": 17.28,
            "roe": 0.16,
            "roce": 0.22
        }
    ]

@pytest.fixture
def mock_annual_records_hdfcbank():
    return [
        {
            "symbol": "HDFCBANK",
            "period": "2023-03-31",
            "revenue": 2000.0,
            "net_profit": 500.0,
            "eps": 20.0,
            "roe": 0.20,
            "roce": 0.25
        },
        {
            "symbol": "HDFCBANK",
            "period": "2024-03-31",
            "revenue": 1900.0,
            "net_profit": 450.0,
            "eps": 18.0,
            "roe": 0.15,
            "roce": 0.18
        }
    ]

def test_financial_engine_no_annual_records():
    """A. Quarterly-only behavior remains unchanged. H. Missing annual data."""
    res = analyze_financial_health("INFY")

    # Existing keys
    assert "status" in res
    assert "overall_score" in res
    assert "component_statuses" in res

    # New keys should be None
    assert "annual" in res
    assert "red_flags" in res
    assert res["annual"] is None
    assert res["red_flags"] is None

def test_financial_engine_empty_annual_records():
    """I. Empty annual data."""
    res = analyze_financial_health("INFY", annual_records=[])
    assert res["annual"] is None
    assert res["red_flags"] is None

def test_financial_engine_with_annual_records(mock_annual_records_infy):
    """B. Quarterly + annual input. D, E. CAGR correctly populated."""
    res = analyze_financial_health("INFY", annual_records=mock_annual_records_infy)

    assert res["annual"] is not None
    assert res["red_flags"] is not None

    ann = res["annual"]
    assert ann["status"] == "VALID"
    assert ann["revenue_cagr"] == pytest.approx(10.0, rel=1e-2)
    assert ann["net_profit_cagr"] == pytest.approx(20.0, rel=1e-2)

    flags = res["red_flags"]
    assert flags["has_red_flags"] is False
    assert len(flags["red_flags"]) == 0

def test_financial_engine_with_red_flags(mock_annual_records_hdfcbank):
    """F, G. Multiple red flags appear correctly."""
    res = analyze_financial_health("HDFCBANK", annual_records=mock_annual_records_hdfcbank)

    assert res["annual"] is not None
    assert res["red_flags"] is not None

    flags = res["red_flags"]
    assert flags["has_red_flags"] is True
    # HDFC mock is declining in revenue, net_profit, roe, roce => 4 flags
    assert len(flags["red_flags"]) == 4

def test_financial_engine_missing_eps():
    """K. Missing EPS does not break the engine."""
    records = [
        {"symbol": "TCS", "period": "2023-03-31", "revenue": 1000.0, "net_profit": 100.0, "eps": None, "roe": 0.1, "roce": 0.1},
        {"symbol": "TCS", "period": "2024-03-31", "revenue": 1100.0, "net_profit": 110.0, "eps": None, "roe": 0.1, "roce": 0.1}
    ]
    res = analyze_financial_health("TCS", annual_records=records)
    assert res["annual"]["status"] == "VALID"
    assert res["annual"]["latest_eps"] is None
    assert res["red_flags"]["has_red_flags"] is False

def test_financial_engine_insufficient_annual_history():
    """J. Insufficient annual history."""
    records = [
        {"symbol": "WIPRO", "period": "2024-03-31", "revenue": 1000.0, "net_profit": 100.0, "eps": 10.0, "roe": 0.1, "roce": 0.1}
    ]
    res = analyze_financial_health("WIPRO", annual_records=records)

    # One record is PARTIAL, no growth calculated, no red flags
    assert res["annual"]["status"] == "PARTIAL"
    assert res["red_flags"]["has_red_flags"] is False

def test_financial_engine_malformed_input():
    """N. Malformed annual input."""
    # Pass arbitrary string instead of list
    res = analyze_financial_health("RELIANCE", annual_records="this is clearly not a list of dicts") # type: ignore

    assert res["annual"] is None
    assert res["red_flags"] is None

def test_structured_output_types(mock_annual_records_infy):
    """P. Structured output keys and types."""
    res = analyze_financial_health("INFY", annual_records=mock_annual_records_infy)

    assert isinstance(res["annual"], dict)
    assert isinstance(res["red_flags"], dict)
    assert isinstance(res["red_flags"]["has_red_flags"], bool)
    assert isinstance(res["red_flags"]["red_flags"], list)
