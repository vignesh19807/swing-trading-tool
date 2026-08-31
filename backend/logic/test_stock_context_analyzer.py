"""
Unit Tests for Stock Context Analyzer
=====================================
Validates the Stock -> Sector/Industry mapping behavior, missing symbol fallbacks,
and explicit consumption of the Data Engineer classification_service boundary.
"""
import pytest
from backend.logic.stock_context_analyzer import get_stock_context

# Mock Data
MOCK_CLASSIFICATIONS = {
    "INFY": {
        "symbol": "INFY",
        "company_name": "Infosys Limited",
        "sector": "Information Technology",
        "industry": "IT Services"
    },
    "TCS": {
        "symbol": "TCS",
        "company_name": "Tata Consultancy Services Limited",
        "sector": "Information Technology",
        "industry": "IT Services"
    },
    "WIPRO": {
        "symbol": "WIPRO",
        "company_name": "Wipro Limited",
        "sector": "Information Technology",
        "industry": "IT Services"
    },
    "HDFCBANK": {
        "symbol": "HDFCBANK",
        "company_name": "HDFC Bank Limited",
        "sector": "Financial Services",
        "industry": "Banks"
    },
    "RELIANCE": {
        "symbol": "RELIANCE",
        "company_name": "Reliance Industries Limited",
        "sector": "Oil, Gas & Consumable Fuels",
        "industry": "Oil & Gas"
    }
}

def mock_get_company_classification(symbol: str):
    return MOCK_CLASSIFICATIONS.get(symbol, None)

def mock_get_sector_stocks(sector: str):
    if sector == "Information Technology": return ["INFY", "TCS", "WIPRO"]
    if sector == "Financial Services": return ["HDFCBANK"]
    if sector == "Capital Goods": return ["BEL"] # Mock single stock
    return []

def mock_get_industry_stocks(industry: str):
    if industry == "IT Services": return ["INFY", "TCS", "WIPRO"]
    if industry == "Banks": return ["HDFCBANK"]
    return []

@pytest.fixture(autouse=True)
def apply_classification_mocks(monkeypatch):
    """Ensure tests do not hit the live database."""
    monkeypatch.setattr(
        "backend.logic.stock_context_analyzer.get_company_classification",
        mock_get_company_classification
    )
    monkeypatch.setattr(
        "backend.logic.stock_context_analyzer.get_sector_stocks",
        mock_get_sector_stocks
    )
    monkeypatch.setattr(
        "backend.logic.stock_context_analyzer.get_industry_stocks",
        mock_get_industry_stocks
    )

def test_valid_stock_mappings():
    """Verify that recognized symbols return valid mappings and keys."""
    for symbol, expected in MOCK_CLASSIFICATIONS.items():
        result = get_stock_context(symbol)

        assert result["status"] == "VALID"
        assert result["symbol"] == expected["symbol"]
        assert result["company_name"] == expected["company_name"]
        assert result["sector"] == expected["sector"]
        assert result["industry"] == expected["industry"]

def test_unknown_symbol():
    """Verify missing symbol behavior."""
    result = get_stock_context("UNKNOWN_TICKER")

    assert result["status"] == "NOT_FOUND"
    assert result["symbol"] == "UNKNOWN_TICKER"
    assert result["company_name"] is None
    assert result["sector"] is None
    assert result["industry"] is None

def test_empty_invalid_symbol():
    """Verify empty or invalid symbol handling."""
    # Test empty string
    empty_res = get_stock_context("")
    assert empty_res["status"] == "NOT_FOUND"
    assert empty_res["symbol"] == "UNKNOWN"

    # Test None
    none_res = get_stock_context(None)
    assert none_res["status"] == "NOT_FOUND"
    assert none_res["symbol"] == "UNKNOWN"

    # Test whitespace
    ws_res = get_stock_context("   ")
    assert ws_res["status"] == "NOT_FOUND"
    assert ws_res["symbol"] == "UNKNOWN"

def test_deterministic_output():
    """Verify that multiple calls with the same input yield identical results."""
    res1 = get_stock_context("INFY")
    res2 = get_stock_context("INFY")
    assert res1 == res2

    # Verify casing determinism
    res3 = get_stock_context("infy")
    res4 = get_stock_context("InFy ")
    assert res4 == res1

from backend.logic.stock_context_analyzer import get_sector_contexts, get_industry_contexts

def test_get_sector_contexts_valid():
    """Verify multiple valid sector filters return properly formatted lists of dictionaries."""
    it_res = get_sector_contexts("Information Technology")
    assert isinstance(it_res, list)
    assert len(it_res) == 3
    assert it_res[0]["symbol"] == "INFY"
    assert it_res[0]["sector"] == "Information Technology"
    assert it_res[1]["symbol"] == "TCS"
    assert it_res[2]["symbol"] == "WIPRO"

    fin_res = get_sector_contexts("Financial Services")
    assert len(fin_res) == 1
    assert fin_res[0]["symbol"] == "HDFCBANK"

    # Capital goods has an unknown symbol in our MOCK_CLASSIFICATIONS (BEL isn't defined there),
    # it should return a NOT_FOUND struct but still be in the array because the sector returned the symbol.
    cap_res = get_sector_contexts("Capital Goods")
    assert len(cap_res) == 1
    assert cap_res[0]["symbol"] == "BEL"
    assert cap_res[0]["status"] == "NOT_FOUND"

def test_get_industry_contexts_valid():
    """Verify valid industry filters return correctly."""
    it_res = get_industry_contexts("IT Services")
    assert len(it_res) == 3

    bank_res = get_industry_contexts("Banks")
    assert len(bank_res) == 1
    assert bank_res[0]["industry"] == "Banks"

def test_unknown_filters():
    """Verify unknown sectors and industries return empty lists."""
    assert get_sector_contexts("Unknown Sector") == []
    assert get_industry_contexts("Unknown Industry") == []

def test_empty_filters():
    """Verify None, empty string, or whitespace string return empty lists."""
    assert get_sector_contexts("") == []
    assert get_sector_contexts(None) == []
    assert get_sector_contexts("   ") == []

    assert get_industry_contexts("") == []
    assert get_industry_contexts(None) == []
    assert get_industry_contexts("   ") == []

def test_deterministic_ordering():
    """Verify the outputs maintain ordering provided by the Data Engineer mock."""
    res1 = get_sector_contexts("Information Technology")
    res2 = get_sector_contexts("Information Technology")

    assert [ctx["symbol"] for ctx in res1] == ["INFY", "TCS", "WIPRO"]
    assert res1 == res2

from backend.logic.stock_context_analyzer import get_stock_sector_performance_context

def mock_calculate_constituent_returns(symbol, evaluation_date, lookback_periods):
    if symbol == "UNKNOWN":
        return None
    return {"21D": 0.05, "63D": 0.12}

def mock_evaluate_sector(sector, evaluation_date, lookback_periods):
    return {
        "data_quality": {"status": "VALID"},
        "performance": {"21D": 0.04, "63D": 0.10},
        "preliminary_score": {"score": 85.0},
        "relative_strength": {"status": "UNAVAILABLE"}
    }

@pytest.fixture(autouse=True)
def apply_performance_mocks(monkeypatch):
    monkeypatch.setattr(
        "backend.logic.stock_context_analyzer.calculate_constituent_returns",
        mock_calculate_constituent_returns
    )
    monkeypatch.setattr(
        "backend.logic.stock_context_analyzer.evaluate_sector",
        mock_evaluate_sector
    )

def test_stock_sector_performance_valid():
    """Verify valid stock returns correctly unified dictionary."""
    res = get_stock_sector_performance_context("INFY", "2025-10-10")

    assert res["symbol"] == "INFY"
    assert res["evaluation_date"] == "2025-10-10"
    assert res["status"] == "VALID"
    assert res["classification"]["sector"] == "Information Technology"
    assert res["stock_performance"]["21D"] == 0.05
    assert res["sector_performance"]["performance"]["21D"] == 0.04
    assert res["sector_performance"]["preliminary_score"]["score"] == 85.0

def test_stock_sector_performance_unknown():
    """Verify unknown stock returns safe fallback without crashing."""
    res = get_stock_sector_performance_context("UNKNOWN_TICKER")

    assert res["symbol"] == "UNKNOWN_TICKER"
    assert res["status"] == "NOT_FOUND"
    assert res["stock_performance"] is None
    assert res["sector_performance"] is None
